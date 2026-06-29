# src/messages.py
"""
تمام پیام‌های متنی بات — Markdown format
"""

def welcome_new(name: str) -> str:
    return (
        f"👋 سلام *{name}*!\n\n"
        "🏟 به *OSM Football Bot* خوش اومدی.\n\n"
        "برای شروع، یه لیگ و تیم انتخاب کن:"
    )


def club_overview(manager: dict, squad_count: int) -> str:
    return (
        f"🏟 *{manager['club_name']}*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👔 Manager: {manager['name']}\n"
        f"💰 Budget: €{int(manager['budget']):,}\n"
        f"👥 Squad: {squad_count} players\n"
        f"🎯 Formation: `{manager['tactic_formation']}`\n"
        f"⚙️ Style: `{manager['tactic_style']}`\n"
        f"⭐ Manager Points: {manager['manager_points']}"
    )


def squad_header(club_name: str, players: list) -> str:
    pos_order = ['GK', 'DEF', 'MID', 'ATT']
    pos_emoji = {'GK': '🧤', 'DEF': '🛡', 'MID': '⚙️', 'ATT': '⚡'}
    lines = [f"👥 *Squad — {club_name}*", "━━━━━━━━━━━━━━━━━━━"]

    avg = sum(p['rating'] for p in players) / len(players) if players else 0
    lines.append(f"📊 Team Rating: *{avg:.1f}*\n")

    for pos in pos_order:
        group = [p for p in players if p['position'] == pos]
        if group:
            lines.append(f"{pos_emoji[pos]} *{pos}*")
            for p in group:
                stamina_bar = stamina_emoji(p['stamina'])
                lines.append(
                    f"  • {p['name']} — {p['rating']:.0f} {stamina_bar}"
                )

    return "\n".join(lines)


def player_detail(p: dict) -> str:
    value_str = f"€{int(p['value']):,}" if p.get('value') else "N/A"
    sale_str = "✅ Listed for Sale" if p.get('for_sale') else "❌ Not for Sale"
    return (
        f"👤 *{p['name']}*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Position: {p['position']}\n"
        f"⭐ Rating: *{p['rating']:.1f}*\n"
        f"🎂 Age: {p['age']}\n"
        f"💪 Stamina: {p['stamina']:.0f}/100 {stamina_emoji(p['stamina'])}\n"
        f"💰 Value: {value_str}\n"
        f"🏷 Status: {sale_str}"
    )


def standings_table(standings: list, user_club_id: int = None) -> str:
    lines = ["🏆 *League Standings*", "━━━━━━━━━━━━━━━━━━━"]
    lines.append("`#   Club              P   W  D  L  GD  Pts`")

    for i, s in enumerate(standings, 1):
        marker = "👉" if s['club_id'] == user_club_id else "  "
        name = s['club_name'][:14].ljust(14)
        gd = s['goals_for'] - s['goals_against']
        gd_str = f"+{gd}" if gd > 0 else str(gd)
        lines.append(
            f"`{marker}{i:2}. {name} {s['played']:2}  {s['wins']:2} "
            f"{s['draws']:2} {s['losses']:2} {gd_str:>4} {s['points']:3}`"
        )

    return "\n".join(lines)


def fixtures_list(matches: list, current_round: int) -> str:
    lines = [f"📋 *Round {current_round} Fixtures*", "━━━━━━━━━━━━━━━━━━━"]
    for m in matches:
        status = "✅" if m['played'] else "🕐"
        if m['played']:
            lines.append(
                f"{status} {m['home_name']} *{m['home_goals']}–{m['away_goals']}* {m['away_name']}"
            )
        else:
            lines.append(f"{status} {m['home_name']} vs {m['away_name']}")
    return "\n".join(lines)


def transfer_market_header(players: list) -> str:
    lines = ["🔄 *Transfer Market*", "━━━━━━━━━━━━━━━━━━━",
             "بازیکنان موجود برای خرید:\n"]
    pos_emoji = {'GK': '🧤', 'DEF': '🛡', 'MID': '⚙️', 'ATT': '⚡'}
    for p in players:
        emoji = pos_emoji.get(p['position'], '👤')
        lines.append(
            f"{emoji} *{p['name']}* ({p['club_name']})\n"
            f"   Rating: {p['rating']:.0f} | Age: {p['age']} | €{int(p['value']):,}"
        )
    return "\n".join(lines)


def offer_received(player_name: str, fee: float, from_club: str) -> str:
    return (
        f"📬 *پیشنهاد جدید!*\n\n"
        f"تیم *{from_club}* برای *{player_name}* "
        f"مبلغ *€{int(fee):,}* پیشنهاد داده.\n\n"
        f"قبول می‌کنی؟"
    )


def training_success(player_name: str) -> str:
    return f"🏋️ *{player_name}* تمرین کرد!\n⭐ Rating +0.2 | 💪 Stamina +15"


def training_already_done(player_name: str) -> str:
    return f"⏰ *{player_name}* امروز قبلاً تمرین کرده.\nفردا دوباره بیا!"


def season_complete(champion_name: str) -> str:
    return (
        f"🎉 *Season Complete!*\n\n"
        f"🏆 Champion: *{champion_name}*\n\n"
        f"سیزن جدید آماده‌ست. تیمت رو برای فصل بعد آماده کن!"
    )


def stamina_emoji(stamina: float) -> str:
    if stamina >= 80:
        return "🟢"
    elif stamina >= 50:
        return "🟡"
    else:
        return "🔴"


def error_msg(text: str = "مشکلی پیش اومد. دوباره امتحان کن.") -> str:
    return f"❌ {text}"


def not_registered() -> str:
    return "⚠️ اول باید ثبت‌نام کنی. دستور /start رو بزن."
