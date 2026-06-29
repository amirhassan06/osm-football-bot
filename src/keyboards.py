# src/keyboards.py
"""
تمام Inline Keyboard های بات
"""

def main_menu(club_name: str = '') -> dict:
    title = f"🏟 {club_name}" if club_name else "🏟 My Club"
    return {
        "inline_keyboard": [
            [
                {"text": title,           "callback_data": "menu_club"},
                {"text": "📅 Season",     "callback_data": "menu_season"},
            ],
            [
                {"text": "🔄 Transfers",  "callback_data": "menu_transfers"},
                {"text": "🏋️ Training",   "callback_data": "menu_training"},
            ],
            [
                {"text": "📊 Standings",  "callback_data": "menu_standings"},
                {"text": "📈 My Stats",   "callback_data": "menu_stats"},
            ],
        ]
    }


def club_menu() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "👥 Squad",         "callback_data": "club_squad"}],
            [{"text": "🎯 Tactics",       "callback_data": "club_tactics"}],
            [{"text": "💼 Budget",        "callback_data": "club_budget"}],
            [{"text": "🔙 Back",          "callback_data": "back_main"}],
        ]
    }


def squad_menu(players: list, page: int = 0) -> dict:
    """نمایش بازیکنان با pagination"""
    PAGE_SIZE = 6
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_players = players[start:end]

    pos_emoji = {'GK': '🧤', 'DEF': '🛡', 'MID': '⚙️', 'ATT': '⚡'}
    rows = []

    for p in page_players:
        emoji = pos_emoji.get(p['position'], '👤')
        label = f"{emoji} {p['name']} ({p['rating']:.0f})"
        rows.append([{"text": label, "callback_data": f"player_{p['id']}"}])

    nav = []
    if page > 0:
        nav.append({"text": "◀️ Prev", "callback_data": f"squad_page_{page-1}"})
    if end < len(players):
        nav.append({"text": "Next ▶️", "callback_data": f"squad_page_{page+1}"})
    if nav:
        rows.append(nav)

    rows.append([{"text": "🔙 Back", "callback_data": "menu_club"}])
    return {"inline_keyboard": rows}


def player_detail_menu(player_id: int, is_own_club: bool = True) -> dict:
    rows = []
    if is_own_club:
        rows.append([
            {"text": "🏋️ Train",       "callback_data": f"train_{player_id}"},
            {"text": "💲 List for Sale","callback_data": f"list_sale_{player_id}"},
        ])
    rows.append([{"text": "🔙 Back to Squad", "callback_data": "club_squad"}])
    return {"inline_keyboard": rows}


def tactics_formation_menu() -> dict:
    formations = ["4-4-2", "4-3-3", "3-5-2", "4-2-3-1", "5-3-2"]
    rows = [[{"text": f, "callback_data": f"formation_{f}"}] for f in formations]
    rows.append([{"text": "🔙 Back", "callback_data": "menu_club"}])
    return {"inline_keyboard": rows}


def tactics_style_menu(formation: str) -> dict:
    styles = [
        ("⚔️ Attacking",   "attacking"),
        ("⚖️ Balanced",    "balanced"),
        ("🛡 Defensive",   "defensive"),
        ("↩️ Counter",     "counter"),
        ("🎯 Possession",  "possession"),
    ]
    rows = [[{"text": label, "callback_data": f"style_{s}_{formation}"}]
            for label, s in styles]
    rows.append([{"text": "🔙 Back", "callback_data": "club_tactics"}])
    return {"inline_keyboard": rows}


def season_menu() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "📋 Fixtures",         "callback_data": "season_fixtures"}],
            [{"text": "⏭ Simulate Next Round","callback_data": "season_simulate"}],
            [{"text": "🏆 Results",           "callback_data": "season_results"}],
            [{"text": "🔙 Back",              "callback_data": "back_main"}],
        ]
    }


def transfers_menu() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "🔍 Browse Market",   "callback_data": "transfer_browse"}],
            [{"text": "📬 Incoming Offers", "callback_data": "transfer_incoming"}],
            [{"text": "🔙 Back",            "callback_data": "back_main"}],
        ]
    }


def transfer_player_menu(player_id: int, player_value: float) -> dict:
    """پیشنهاد قیمت به بازیکن در مارکت"""
    offers = [0.8, 0.9, 1.0, 1.1]
    rows = []
    for mult in offers:
        fee = int(player_value * mult)
        label = f"{'💰' if mult >= 1.0 else '💸'} €{fee:,} ({int(mult*100)}%)"
        rows.append([{"text": label, "callback_data": f"make_offer_{player_id}_{fee}"}])
    rows.append([{"text": "🔙 Back", "callback_data": "transfer_browse"}])
    return {"inline_keyboard": rows}


def incoming_offer_menu(transfer_id: int) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Accept", "callback_data": f"offer_accept_{transfer_id}"},
                {"text": "❌ Reject", "callback_data": f"offer_reject_{transfer_id}"},
            ]
        ]
    }


def league_select_menu(leagues: list) -> dict:
    rows = [[{"text": f"🌍 {l['name']} ({l['country']})",
              "callback_data": f"select_league_{l['id']}"}]
            for l in leagues]
    return {"inline_keyboard": rows}


def club_select_menu(clubs: list) -> dict:
    rows = [[{"text": f"🏟 {c['name']}", "callback_data": f"select_club_{c['id']}"}]
            for c in clubs]
    return {"inline_keyboard": rows}


def confirm_simulate_menu(league_id: int, round_num: int) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": f"▶️ Play Round {round_num}",
                 "callback_data": f"confirm_simulate_{league_id}"},
                {"text": "❌ Cancel", "callback_data": "menu_season"},
            ]
        ]
    }
