# src/db.py
"""
توابع دیتابیس — D1 (SQLite) روی Cloudflare Workers
همه توابع async هستند چون D1 binding در Workers اینگونه کار می‌کند
"""

import json


# ───────────────────────────── Managers ──────────────────────────────

async def get_manager(db, telegram_id: int) -> dict | None:
    result = await db.prepare(
        "SELECT m.*, c.name as club_name, c.tactic_formation, c.tactic_style, "
        "c.budget, c.id as club_id FROM managers m "
        "LEFT JOIN clubs c ON m.club_id = c.id "
        "WHERE m.telegram_id = ?"
    ).bind(telegram_id).first()
    return result


async def create_manager(db, telegram_id: int, username: str, name: str) -> int:
    result = await db.prepare(
        "INSERT OR IGNORE INTO managers (telegram_id, username, name) VALUES (?, ?, ?)"
    ).bind(telegram_id, username or '', name or '').run()
    return result.meta.last_row_id


async def assign_club(db, telegram_id: int, club_id: int):
    await db.prepare(
        "UPDATE managers SET club_id = ? WHERE telegram_id = ?"
    ).bind(club_id, telegram_id).run()
    await db.prepare(
        "UPDATE clubs SET manager_id = ? WHERE id = ?"
    ).bind(telegram_id, club_id).run()


async def add_manager_points(db, telegram_id: int, points: int):
    await db.prepare(
        "UPDATE managers SET manager_points = manager_points + ? WHERE telegram_id = ?"
    ).bind(points, telegram_id).run()


# ───────────────────────────── Leagues ───────────────────────────────

async def get_all_leagues(db) -> list:
    result = await db.prepare("SELECT * FROM leagues ORDER BY name").all()
    return result.results or []


async def get_league(db, league_id: int) -> dict | None:
    return await db.prepare("SELECT * FROM leagues WHERE id = ?").bind(league_id).first()


async def advance_round(db, league_id: int):
    await db.prepare(
        "UPDATE leagues SET current_round = current_round + 1 WHERE id = ?"
    ).bind(league_id).run()


# ───────────────────────────── Clubs ─────────────────────────────────

async def get_clubs_by_league(db, league_id: int) -> list:
    result = await db.prepare(
        "SELECT c.*, m.username as manager_username FROM clubs c "
        "LEFT JOIN managers m ON c.manager_id = m.telegram_id "
        "WHERE c.league_id = ? ORDER BY c.name"
    ).bind(league_id).all()
    return result.results or []


async def get_club(db, club_id: int) -> dict | None:
    return await db.prepare("SELECT * FROM clubs WHERE id = ?").bind(club_id).first()


async def get_free_clubs(db, league_id: int) -> list:
    """تیم‌هایی که مدیر انسانی ندارند"""
    result = await db.prepare(
        "SELECT * FROM clubs WHERE league_id = ? AND manager_id IS NULL ORDER BY name"
    ).bind(league_id).all()
    return result.results or []


async def update_tactic(db, club_id: int, formation: str, style: str):
    await db.prepare(
        "UPDATE clubs SET tactic_formation = ?, tactic_style = ? WHERE id = ?"
    ).bind(formation, style, club_id).run()


async def update_budget(db, club_id: int, delta: float):
    await db.prepare(
        "UPDATE clubs SET budget = budget + ? WHERE id = ?"
    ).bind(delta, club_id).run()


# ───────────────────────────── Players ───────────────────────────────

async def get_squad(db, club_id: int) -> list:
    result = await db.prepare(
        "SELECT * FROM players WHERE club_id = ? ORDER BY "
        "CASE position WHEN 'GK' THEN 1 WHEN 'DEF' THEN 2 "
        "WHEN 'MID' THEN 3 WHEN 'ATT' THEN 4 END, rating DESC"
    ).bind(club_id).all()
    return result.results or []


async def get_player(db, player_id: int) -> dict | None:
    return await db.prepare("SELECT * FROM players WHERE id = ?").bind(player_id).first()


async def get_players_for_sale(db, exclude_club_id: int) -> list:
    result = await db.prepare(
        "SELECT p.*, c.name as club_name FROM players p "
        "JOIN clubs c ON p.club_id = c.id "
        "WHERE p.for_sale = 1 AND p.club_id != ? "
        "ORDER BY p.rating DESC LIMIT 20"
    ).bind(exclude_club_id).all()
    return result.results or []


async def transfer_player(db, player_id: int, to_club_id: int):
    await db.prepare(
        "UPDATE players SET club_id = ?, for_sale = 0 WHERE id = ?"
    ).bind(to_club_id, player_id).run()


async def update_stamina(db, club_id: int, delta: float):
    """کاهش stamina بعد از بازی"""
    await db.prepare(
        "UPDATE players SET stamina = MAX(20, MIN(100, stamina + ?)) WHERE club_id = ?"
    ).bind(delta, club_id).run()


async def train_player(db, player_id: int, club_id: int) -> bool:
    """
    Training یک بازیکن — روزی یک بار
    Returns True اگر موفق، False اگر امروز قبلاً train شده
    """
    today = "date('now')"
    already = await db.prepare(
        f"SELECT id FROM training_log WHERE player_id = ? AND club_id = ? "
        f"AND DATE(trained_at) = {today}"
    ).bind(player_id, club_id).first()

    if already:
        return False

    await db.prepare(
        "UPDATE players SET rating = MIN(99, rating + 0.2), "
        "stamina = MIN(100, stamina + 15) WHERE id = ? AND club_id = ?"
    ).bind(player_id, club_id).run()

    await db.prepare(
        "INSERT INTO training_log (club_id, player_id, rating_boost, stamina_boost) "
        "VALUES (?, ?, 0.2, 15)"
    ).bind(club_id, player_id).run()

    return True


# ───────────────────────────── Matches ───────────────────────────────

async def get_upcoming_matches(db, league_id: int, round_num: int) -> list:
    result = await db.prepare(
        "SELECT m.*, "
        "h.name as home_name, a.name as away_name "
        "FROM matches m "
        "JOIN clubs h ON m.home_club_id = h.id "
        "JOIN clubs a ON m.away_club_id = a.id "
        "WHERE m.league_id = ? AND m.round_num = ? AND m.played = 0"
    ).bind(league_id, round_num).all()
    return result.results or []


async def save_match_result(db, match_id: int, home_goals: int, away_goals: int, events: list):
    await db.prepare(
        "UPDATE matches SET home_goals = ?, away_goals = ?, events_json = ?, played = 1 "
        "WHERE id = ?"
    ).bind(home_goals, away_goals, json.dumps(events), match_id).run()


async def get_recent_results(db, club_id: int, limit: int = 5) -> list:
    result = await db.prepare(
        "SELECT m.*, h.name as home_name, a.name as away_name "
        "FROM matches m "
        "JOIN clubs h ON m.home_club_id = h.id "
        "JOIN clubs a ON m.away_club_id = a.id "
        "WHERE (m.home_club_id = ? OR m.away_club_id = ?) AND m.played = 1 "
        "ORDER BY m.id DESC LIMIT ?"
    ).bind(club_id, club_id, limit).all()
    return result.results or []


# ───────────────────────────── Standings ─────────────────────────────

async def get_standings(db, league_id: int) -> list:
    result = await db.prepare(
        "SELECT s.*, c.name as club_name, c.manager_id "
        "FROM standings s JOIN clubs c ON s.club_id = c.id "
        "WHERE s.league_id = ? "
        "ORDER BY s.points DESC, (s.goals_for - s.goals_against) DESC, s.goals_for DESC"
    ).bind(league_id).all()
    return result.results or []


async def update_standings(db, league_id: int, home_id: int, away_id: int,
                           home_goals: int, away_goals: int):
    if home_goals > away_goals:
        hw, hd, hl = 1, 0, 0
        aw, ad, al = 0, 0, 1
        hp, ap = 3, 0
    elif home_goals < away_goals:
        hw, hd, hl = 0, 0, 1
        aw, ad, al = 1, 0, 0
        hp, ap = 0, 3
    else:
        hw, hd, hl = 0, 1, 0
        aw, ad, al = 0, 1, 0
        hp, ap = 1, 1

    await db.prepare(
        "UPDATE standings SET played=played+1, wins=wins+?, draws=draws+?, losses=losses+?, "
        "goals_for=goals_for+?, goals_against=goals_against+?, points=points+? "
        "WHERE league_id=? AND club_id=?"
    ).bind(hw, hd, hl, home_goals, away_goals, hp, league_id, home_id).run()

    await db.prepare(
        "UPDATE standings SET played=played+1, wins=wins+?, draws=draws+?, losses=losses+?, "
        "goals_for=goals_for+?, goals_against=goals_against+?, points=points+? "
        "WHERE league_id=? AND club_id=?"
    ).bind(aw, ad, al, away_goals, home_goals, ap, league_id, away_id).run()


# ───────────────────────────── Transfers ─────────────────────────────

async def create_offer(db, player_id: int, from_club: int, to_club: int,
                       fee: float, offered_by: int) -> int:
    result = await db.prepare(
        "INSERT INTO transfers (player_id, from_club_id, to_club_id, fee, offered_by) "
        "VALUES (?, ?, ?, ?, ?)"
    ).bind(player_id, from_club, to_club, fee, offered_by).run()
    return result.meta.last_row_id


async def get_pending_offers(db, club_id: int) -> list:
    result = await db.prepare(
        "SELECT t.*, p.name as player_name, p.position, p.rating, p.value, "
        "c.name as from_club_name "
        "FROM transfers t "
        "JOIN players p ON t.player_id = p.id "
        "JOIN clubs c ON t.from_club_id = c.id "
        "WHERE t.to_club_id = ? AND t.status = 'pending'"
    ).bind(club_id).all()
    return result.results or []


async def resolve_offer(db, transfer_id: int, accept: bool):
    status = 'accepted' if accept else 'rejected'
    await db.prepare(
        "UPDATE transfers SET status = ? WHERE id = ?"
    ).bind(status, transfer_id).run()
