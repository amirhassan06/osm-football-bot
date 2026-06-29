# src/index.py
"""
OSM Football Bot — Cloudflare Python Workers
Entry point: webhook handler

Deploy:
  wrangler deploy

Set webhook:
  curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<worker>.workers.dev/webhook&secret_token=<SECRET>"
"""

import json
from js import Response, fetch, Headers  # Cloudflare Workers JS interop

from db import (
    get_manager, create_manager, assign_club, add_manager_points,
    get_all_leagues, get_league, advance_round,
    get_clubs_by_league, get_club, get_free_clubs, update_tactic, update_budget,
    get_squad, get_player, get_players_for_sale, transfer_player, update_stamina,
    train_player,
    get_upcoming_matches, save_match_result, get_recent_results,
    get_standings, update_standings,
    create_offer, get_pending_offers, resolve_offer,
)
from simulator import simulate_match, format_match_result
from keyboards import (
    main_menu, club_menu, squad_menu, player_detail_menu,
    tactics_formation_menu, tactics_style_menu,
    season_menu, transfers_menu, transfer_player_menu,
    incoming_offer_menu, league_select_menu, club_select_menu,
    confirm_simulate_menu,
)
from messages import (
    welcome_new, club_overview, squad_header, player_detail,
    standings_table, fixtures_list, transfer_market_header,
    offer_received, training_success, training_already_done,
    error_msg, not_registered,
)

# ─────────────────────────── Telegram API ────────────────────────────

async def tg_call(token: str, method: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    resp = await fetch(
        url,
        method="POST",
        headers={"Content-Type": "application/json"},
        body=json.dumps(payload),
    )
    return await resp.json()


async def send_message(token: str, chat_id: int, text: str,
                       keyboard: dict = None, edit_message_id: int = None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if keyboard:
        payload["reply_markup"] = keyboard

    if edit_message_id:
        payload["message_id"] = edit_message_id
        await tg_call(token, "editMessageText", payload)
    else:
        await tg_call(token, "sendMessage", payload)


async def answer_callback(token: str, callback_query_id: str, text: str = ""):
    await tg_call(token, "answerCallbackQuery", {
        "callback_query_id": callback_query_id,
        "text": text,
    })


# ─────────────────────────── Main Entry ──────────────────────────────

async def on_fetch(request, env):
    """Cloudflare Workers entry point"""

    # فقط POST به /webhook قبول می‌کنیم
    if request.method != "POST":
        return Response.new("OSM Bot running ✅", status=200)

    # تأیید secret
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret != env.WEBHOOK_SECRET:
        return Response.new("Unauthorized", status=401)

    try:
        update = await request.json()
        await handle_update(update, env)
    except Exception as e:
        print(f"Error: {e}")

    return Response.new("ok", status=200)


async def handle_update(update: dict, env):
    db = env.DB
    token = env.BOT_TOKEN

    if "message" in update:
        await handle_message(update["message"], db, token)
    elif "callback_query" in update:
        await handle_callback(update["callback_query"], db, token)


# ─────────────────────────── Message Handler ─────────────────────────

async def handle_message(msg: dict, db, token: str):
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")
    user = msg["from"]
    username = user.get("username", "")
    name = user.get("first_name", "") + " " + user.get("last_name", "")
    name = name.strip() or username or "Manager"

    if text == "/start":
        manager = await get_manager(db, chat_id)
        if manager and manager.get("club_id"):
            # قبلاً ثبت شده — نمایش منوی اصلی
            await send_message(
                token, chat_id,
                f"👋 خوش برگشتی *{manager['name']}*!",
                main_menu(manager.get("club_name", ""))
            )
        else:
            # ثبت‌نام جدید
            await create_manager(db, chat_id, username, name)
            leagues = await get_all_leagues(db)
            if not leagues:
                await send_message(token, chat_id,
                    "⚠️ هنوز لیگی در دیتابیس نیست.\n"
                    "ادمین باید اول seed SQL رو اجرا کنه.")
                return
            await send_message(
                token, chat_id,
                welcome_new(name),
                league_select_menu(leagues)
            )

    elif text == "/menu":
        manager = await get_manager(db, chat_id)
        if not manager or not manager.get("club_id"):
            await send_message(token, chat_id, not_registered())
            return
        await send_message(
            token, chat_id, "📋 منوی اصلی:",
            main_menu(manager.get("club_name", ""))
        )

    elif text == "/standings":
        manager = await get_manager(db, chat_id)
        if not manager or not manager.get("club_id"):
            await send_message(token, chat_id, not_registered())
            return
        club = await get_club(db, manager["club_id"])
        s = await get_standings(db, club["league_id"])
        await send_message(token, chat_id,
            standings_table(s, manager["club_id"]))

    elif text == "/help":
        await send_message(token, chat_id,
            "📖 *OSM Football Bot — راهنما*\n\n"
            "/start — شروع / منوی اصلی\n"
            "/menu — نمایش منو\n"
            "/standings — جدول لیگ\n"
            "/help — این پیام\n\n"
            "از دکمه‌های منو برای بازی استفاده کن! 🎮"
        )


# ─────────────────────────── Callback Handler ────────────────────────

async def handle_callback(cb: dict, db, token: str):
    chat_id = cb["from"]["id"]
    msg_id = cb["message"]["message_id"]
    data = cb.get("data", "")

    await answer_callback(token, cb["id"])

    manager = await get_manager(db, chat_id)

    # ─── Onboarding: league/club selection ───────────────────────────
    if data.startswith("select_league_"):
        league_id = int(data.split("_")[-1])
        clubs = await get_free_clubs(db, league_id)
        if not clubs:
            await send_message(token, chat_id,
                "⚠️ همه تیم‌های این لیگ مدیر دارند. یه لیگ دیگه انتخاب کن.",
                edit_message_id=msg_id)
            return
        await send_message(token, chat_id,
            "🏟 یه تیم انتخاب کن:",
            club_select_menu(clubs), edit_message_id=msg_id)

    elif data.startswith("select_club_"):
        club_id = int(data.split("_")[-1])
        await assign_club(db, chat_id, club_id)
        club = await get_club(db, club_id)
        await send_message(token, chat_id,
            f"✅ تیم *{club['name']}* رو قبول کردی!\n\n"
            f"💰 بودجه: €{int(club['budget']):,}\n"
            f"🎯 فرمیشن پیش‌فرض: {club['tactic_formation']}\n\n"
            f"بریم بازی کنیم! 🏆",
            main_menu(club["name"]), edit_message_id=msg_id)

    # ─── Main menu ────────────────────────────────────────────────────
    elif data == "back_main" or data == "menu_main":
        if not manager:
            return
        await send_message(token, chat_id, "📋 منوی اصلی:",
            main_menu(manager.get("club_name", "")), edit_message_id=msg_id)

    elif data == "menu_club":
        if not manager:
            return
        squad = await get_squad(db, manager["club_id"])
        text = club_overview(manager, len(squad))
        await send_message(token, chat_id, text, club_menu(), edit_message_id=msg_id)

    # ─── Club submenu ─────────────────────────────────────────────────
    elif data == "club_squad" or data.startswith("squad_page_"):
        if not manager:
            return
        page = int(data.split("_")[-1]) if data.startswith("squad_page_") else 0
        players = await get_squad(db, manager["club_id"])
        club = await get_club(db, manager["club_id"])
        text = squad_header(club["name"], players)
        await send_message(token, chat_id, text,
            squad_menu(players, page), edit_message_id=msg_id)

    elif data.startswith("player_"):
        if not manager:
            return
        player_id = int(data.split("_")[1])
        p = await get_player(db, player_id)
        if not p:
            return
        is_own = p["club_id"] == manager["club_id"]
        await send_message(token, chat_id,
            player_detail(p),
            player_detail_menu(player_id, is_own), edit_message_id=msg_id)

    elif data == "club_tactics":
        if not manager:
            return
        await send_message(token, chat_id,
            "🎯 فرمیشن رو انتخاب کن:",
            tactics_formation_menu(), edit_message_id=msg_id)

    elif data.startswith("formation_"):
        formation = data.split("_", 1)[1]
        await send_message(token, chat_id,
            f"✅ فرمیشن: `{formation}`\nحالا سبک بازی:",
            tactics_style_menu(formation), edit_message_id=msg_id)

    elif data.startswith("style_"):
        parts = data.split("_", 2)
        style = parts[1]
        formation = parts[2]
        await update_tactic(db, manager["club_id"], formation, style)
        await send_message(token, chat_id,
            f"✅ ذخیره شد!\n🎯 `{formation}` | ⚙️ `{style}`",
            club_menu(), edit_message_id=msg_id)

    elif data == "club_budget":
        if not manager:
            return
        club = await get_club(db, manager["club_id"])
        await send_message(token, chat_id,
            f"💰 بودجه: *€{int(club['budget']):,}*",
            club_menu(), edit_message_id=msg_id)

    # ─── Season ───────────────────────────────────────────────────────
    elif data == "menu_season":
        await send_message(token, chat_id, "📅 Season Menu:",
            season_menu(), edit_message_id=msg_id)

    elif data == "season_fixtures":
        if not manager:
            return
        club = await get_club(db, manager["club_id"])
        league = await get_league(db, club["league_id"])
        round_num = league["current_round"] + 1
        matches = await get_upcoming_matches(db, club["league_id"], round_num)
        text = fixtures_list(matches, round_num)
        await send_message(token, chat_id, text, season_menu(), edit_message_id=msg_id)

    elif data == "season_simulate":
        if not manager:
            return
        club = await get_club(db, manager["club_id"])
        league = await get_league(db, club["league_id"])
        next_round = league["current_round"] + 1

        if next_round > league["total_rounds"]:
            s = await get_standings(db, club["league_id"])
            champion = s[0]["club_name"] if s else "?"
            await send_message(token, chat_id,
                f"🏆 سیزن تموم شد!\nقهرمان: *{champion}*",
                main_menu(club["name"]), edit_message_id=msg_id)
            return

        await send_message(token, chat_id,
            f"⚽ می‌خوای Round {next_round} رو بازی کنی؟",
            confirm_simulate_menu(club["league_id"], next_round),
            edit_message_id=msg_id)

    elif data.startswith("confirm_simulate_"):
        if not manager:
            return
        league_id = int(data.split("_")[-1])
        club = await get_club(db, manager["club_id"])
        league = await get_league(db, league_id)
        round_num = league["current_round"] + 1

        matches = await get_upcoming_matches(db, league_id, round_num)
        result_lines = [f"⚽ *Round {round_num} Results*", "━━━━━━━━━━━━━━━━━━━"]
        user_result = None

        for match in matches:
            home_squad = await get_squad(db, match["home_club_id"])
            away_squad = await get_squad(db, match["away_club_id"])
            home_club  = await get_club(db, match["home_club_id"])
            away_club  = await get_club(db, match["away_club_id"])

            result = simulate_match(
                [dict(p) for p in home_squad],
                [dict(p) for p in away_squad],
                home_club["tactic_style"],
                away_club["tactic_style"],
                home_club["name"],
                away_club["name"],
            )

            await save_match_result(
                db, match["id"],
                result["home_goals"], result["away_goals"],
                result["events"]
            )
            await update_standings(
                db, league_id,
                match["home_club_id"], match["away_club_id"],
                result["home_goals"], result["away_goals"]
            )

            # کاهش stamina
            await update_stamina(db, match["home_club_id"], -10)
            await update_stamina(db, match["away_club_id"], -10)

            # Manager Points
            if match["home_club_id"] == manager["club_id"]:
                pts = 10 if result["home_goals"] > result["away_goals"] else \
                      5  if result["home_goals"] == result["away_goals"] else 0
                await add_manager_points(db, chat_id, pts)
                user_result = format_match_result(result, home_club["name"], away_club["name"])
            elif match["away_club_id"] == manager["club_id"]:
                pts = 10 if result["away_goals"] > result["home_goals"] else \
                      5  if result["home_goals"] == result["away_goals"] else 0
                await add_manager_points(db, chat_id, pts)
                user_result = format_match_result(result, home_club["name"], away_club["name"])

            hg = result["home_goals"]
            ag = result["away_goals"]
            result_lines.append(
                f"{home_club['name']} *{hg}–{ag}* {away_club['name']}"
            )

        await advance_round(db, league_id)

        # ارسال خلاصه نتایج
        await send_message(token, chat_id,
            "\n".join(result_lines), season_menu(), edit_message_id=msg_id)

        # اگر کاربر بازی داشت جزئیات بازیش رو جداگانه بفرست
        if user_result:
            await send_message(token, chat_id,
                f"🎯 *بازی تو:*\n\n{user_result}")

    elif data == "season_results":
        if not manager:
            return
        club = await get_club(db, manager["club_id"])
        results = await get_recent_results(db, manager["club_id"])
        if not results:
            await send_message(token, chat_id,
                "📭 هنوز بازی انجام نشده.", season_menu(), edit_message_id=msg_id)
            return
        lines = ["📊 *نتایج اخیر*", "━━━━━━━━━━━━━━━━━━━"]
        for m in results:
            lines.append(f"⚽ {m['home_name']} *{m['home_goals']}–{m['away_goals']}* {m['away_name']}")
        await send_message(token, chat_id,
            "\n".join(lines), season_menu(), edit_message_id=msg_id)

    # ─── Standings ────────────────────────────────────────────────────
    elif data == "menu_standings":
        if not manager:
            return
        club = await get_club(db, manager["club_id"])
        s = await get_standings(db, club["league_id"])
        await send_message(token, chat_id,
            standings_table(s, manager["club_id"]),
            main_menu(club["name"]), edit_message_id=msg_id)

    # ─── Transfers ────────────────────────────────────────────────────
    elif data == "menu_transfers":
        await send_message(token, chat_id, "🔄 Transfer Market:",
            transfers_menu(), edit_message_id=msg_id)

    elif data == "transfer_browse":
        if not manager:
            return
        players = await get_players_for_sale(db, manager["club_id"])
        if not players:
            await send_message(token, chat_id,
                "📭 هیچ بازیکنی در مارکت نیست.",
                transfers_menu(), edit_message_id=msg_id)
            return
        text = transfer_market_header(players)
        rows = []
        for p in players:
            rows.append([{"text": f"🔍 {p['name']} ({p['rating']:.0f})",
                          "callback_data": f"view_market_{p['id']}"}])
        rows.append([{"text": "🔙 Back", "callback_data": "menu_transfers"}])
        await send_message(token, chat_id, text,
            {"inline_keyboard": rows}, edit_message_id=msg_id)

    elif data.startswith("view_market_"):
        player_id = int(data.split("_")[-1])
        p = await get_player(db, player_id)
        if not p:
            return
        await send_message(token, chat_id,
            player_detail(p),
            transfer_player_menu(player_id, p["value"] or 1000000),
            edit_message_id=msg_id)

    elif data.startswith("make_offer_"):
        if not manager:
            return
        parts = data.split("_")
        player_id = int(parts[2])
        fee = float(parts[3])
        p = await get_player(db, player_id)
        if not p:
            return
        club = await get_club(db, manager["club_id"])
        if club["budget"] < fee:
            await send_message(token, chat_id,
                error_msg("بودجه‌ت کافی نیست! 💸"),
                edit_message_id=msg_id)
            return
        await create_offer(db, player_id, p["club_id"],
                           manager["club_id"], fee, chat_id)
        await send_message(token, chat_id,
            f"📨 پیشنهاد €{int(fee):,} برای *{p['name']}* فرستاده شد!",
            transfers_menu(), edit_message_id=msg_id)

    elif data == "transfer_incoming":
        if not manager:
            return
        offers = await get_pending_offers(db, manager["club_id"])
        if not offers:
            await send_message(token, chat_id,
                "📭 هیچ پیشنهاد ورودی‌ای نداری.",
                transfers_menu(), edit_message_id=msg_id)
            return
        for offer in offers:
            await send_message(token, chat_id,
                offer_received(offer["player_name"], offer["fee"],
                               offer["from_club_name"]),
                incoming_offer_menu(offer["id"]))

    elif data.startswith("offer_accept_"):
        transfer_id = int(data.split("_")[-1])
        # پیدا کردن اطلاعات transfer
        result = await db.prepare(
            "SELECT * FROM transfers WHERE id = ?"
        ).bind(transfer_id).first()
        if not result:
            return
        await resolve_offer(db, transfer_id, accept=True)
        await transfer_player(db, result["player_id"], result["to_club_id"])
        await update_budget(db, result["from_club_id"], result["fee"])
        await update_budget(db, result["to_club_id"], -result["fee"])
        p = await get_player(db, result["player_id"])
        await send_message(token, chat_id,
            f"✅ *{p['name']}* فروخته شد! €{int(result['fee']):,} به بودجه اضافه شد.",
            edit_message_id=msg_id)

    elif data.startswith("offer_reject_"):
        transfer_id = int(data.split("_")[-1])
        await resolve_offer(db, transfer_id, accept=False)
        await send_message(token, chat_id,
            "❌ پیشنهاد رد شد.", edit_message_id=msg_id)

    # ─── Training ─────────────────────────────────────────────────────
    elif data == "menu_training":
        if not manager:
            return
        players = await get_squad(db, manager["club_id"])
        club = await get_club(db, manager["club_id"])
        text = squad_header(club["name"], players)
        rows = []
        for p in players[:8]:  # max 8 نمایش
            rows.append([{"text": f"🏋️ {p['name']} ({p['rating']:.0f} ⭐)",
                          "callback_data": f"train_{p['id']}"}])
        rows.append([{"text": "🔙 Back", "callback_data": "back_main"}])
        await send_message(token, chat_id, text,
            {"inline_keyboard": rows}, edit_message_id=msg_id)

    elif data.startswith("train_"):
        if not manager:
            return
        player_id = int(data.split("_")[1])
        p = await get_player(db, player_id)
        if not p or p["club_id"] != manager["club_id"]:
            await send_message(token, chat_id,
                error_msg("این بازیکن تیم تو نیست!"))
            return
        success = await train_player(db, player_id, manager["club_id"])
        if success:
            await send_message(token, chat_id,
                training_success(p["name"]))
        else:
            await send_message(token, chat_id,
                training_already_done(p["name"]))

    elif data.startswith("list_sale_"):
        if not manager:
            return
        player_id = int(data.split("_")[-1])
        p = await get_player(db, player_id)
        if not p or p["club_id"] != manager["club_id"]:
            return
        await db.prepare(
            "UPDATE players SET for_sale = 1 WHERE id = ?"
        ).bind(player_id).run()
        await send_message(token, chat_id,
            f"✅ *{p['name']}* در مارکت لیست شد.\nقیمت: €{int(p['value'] or 0):,}")

    # ─── Stats ────────────────────────────────────────────────────────
    elif data == "menu_stats":
        if not manager:
            return
        club = await get_club(db, manager["club_id"])
        league = await get_league(db, club["league_id"])
        s_all = await get_standings(db, club["league_id"])
        my_s = next((s for s in s_all if s["club_id"] == manager["club_id"]), {})
        rank = next((i+1 for i, s in enumerate(s_all)
                     if s["club_id"] == manager["club_id"]), "?")

        text = (
            f"📈 *آمار مدیریتی*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👔 {manager['name']}\n"
            f"🏟 {manager['club_name']}\n"
            f"🏆 League: {league['name']}\n"
            f"📊 Rank: #{rank}\n\n"
            f"Played: {my_s.get('played',0)} | "
            f"W:{my_s.get('wins',0)} "
            f"D:{my_s.get('draws',0)} "
            f"L:{my_s.get('losses',0)}\n"
            f"Goals: {my_s.get('goals_for',0)}–{my_s.get('goals_against',0)}\n"
            f"Points: *{my_s.get('points',0)}*\n\n"
            f"⭐ Manager Points: *{manager['manager_points']}*"
        )
        await send_message(token, chat_id, text,
            main_menu(manager["club_name"]), edit_message_id=msg_id)
