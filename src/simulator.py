# src/simulator.py
"""
موتور شبیه‌ساز بازی — Poisson-based
سازگار با Cloudflare Python Workers (no numpy/scipy)
"""

import random
import math
import json

# ضرایب تاکتیک
TACTIC_MODIFIERS = {
    'attacking':   {'xg_mult': 1.25, 'def_mult': 0.85},
    'balanced':    {'xg_mult': 1.00, 'def_mult': 1.00},
    'defensive':   {'xg_mult': 0.80, 'def_mult': 1.20},
    'counter':     {'xg_mult': 0.95, 'def_mult': 1.05},
    'possession':  {'xg_mult': 1.10, 'def_mult': 1.05},
}

# وزن پوزیشن در محاسبه xG
POSITION_WEIGHTS = {
    'GK':  {'att': 0.0, 'def': 0.35},
    'DEF': {'att': 0.1, 'def': 0.40},
    'MID': {'att': 0.25, 'def': 0.15},
    'ATT': {'att': 0.65, 'def': 0.10},
}


def poisson_sample(lam: float) -> int:
    """
    Poisson sampling بدون scipy — Knuth algorithm
    برای lam کوچک (زیر 30) دقیق است
    """
    if lam <= 0:
        return 0
    lam = min(lam, 8.0)  # cap برای واقعی‌بودن نتایج
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


def calc_team_xg(players: list, tactic_style: str) -> tuple[float, float]:
    """
    محاسبه xG حمله و دفاع تیم بر اساس رتبه بازیکنان

    Args:
        players: لیست dict با کلیدهای position, rating, stamina
        tactic_style: یکی از TACTIC_MODIFIERS

    Returns:
        (attack_strength, defense_strength) هر دو normalized
    """
    if not players:
        return 1.0, 1.0

    att_score = 0.0
    def_score = 0.0
    att_weight_sum = 0.0
    def_weight_sum = 0.0

    for p in players:
        pos = p.get('position', 'MID')
        rating = float(p.get('rating', 70))
        stamina = float(p.get('stamina', 100))

        # تأثیر stamina روی عملکرد واقعی
        effective_rating = rating * (0.7 + 0.3 * stamina / 100)

        w = POSITION_WEIGHTS.get(pos, POSITION_WEIGHTS['MID'])
        att_score += effective_rating * w['att']
        def_score += effective_rating * w['def']
        att_weight_sum += w['att']
        def_weight_sum += w['def']

    att_norm = (att_score / att_weight_sum) if att_weight_sum > 0 else 70
    def_norm = (def_score / def_weight_sum) if def_weight_sum > 0 else 70

    # normalize به بازه 0.5–2.0
    att_strength = att_norm / 75
    def_strength = def_norm / 75

    mod = TACTIC_MODIFIERS.get(tactic_style, TACTIC_MODIFIERS['balanced'])
    att_strength *= mod['xg_mult']
    def_strength *= mod['def_mult']

    return att_strength, def_strength


def simulate_match(
    home_players: list,
    away_players: list,
    home_style: str = 'balanced',
    away_style: str = 'balanced',
    home_name: str = 'Home',
    away_name: str = 'Away',
) -> dict:
    """
    شبیه‌سازی کامل یک بازی

    Returns:
        {
          home_goals, away_goals,
          events: [{minute, type, player, team}],
          possession_home, shots_home, shots_away
        }
    """
    home_att, home_def = calc_team_xg(home_players, home_style)
    away_att, away_def = calc_team_xg(away_players, away_style)

    # xG هر تیم = حمله خودش / دفاع حریف × ضریب خانگی
    HOME_ADVANTAGE = 1.12
    base_xg = 1.4  # میانگین گل در فوتبال

    home_xg = base_xg * (home_att / away_def) * HOME_ADVANTAGE
    away_xg = base_xg * (away_att / home_def)

    # clamp
    home_xg = max(0.3, min(home_xg, 5.0))
    away_xg = max(0.3, min(away_xg, 5.0))

    home_goals = poisson_sample(home_xg)
    away_goals = poisson_sample(away_xg)

    # تولید رویدادها
    events = _generate_events(
        home_goals, away_goals,
        home_players, away_players,
        home_name, away_name
    )

    # آمار
    possession_home = int(50 + (home_att - away_att) * 10)
    possession_home = max(35, min(65, possession_home))
    shots_home = int(home_xg * 6 + random.randint(-2, 3))
    shots_away = int(away_xg * 6 + random.randint(-2, 3))

    return {
        'home_goals': home_goals,
        'away_goals': away_goals,
        'events': events,
        'possession_home': possession_home,
        'possession_away': 100 - possession_home,
        'shots_home': max(shots_home, home_goals),
        'shots_away': max(shots_away, away_goals),
    }


def _generate_events(
    home_goals, away_goals,
    home_players, away_players,
    home_name, away_name
) -> list:
    """تولید رویدادهای بازی (گل، کارت)"""
    events = []
    used_minutes = set()

    def rand_minute():
        for _ in range(20):
            m = random.randint(1, 90)
            if m not in used_minutes:
                used_minutes.add(m)
                return m
        return random.randint(1, 90)

    # گل‌های خانه
    att_home = [p for p in home_players if p.get('position') in ('ATT', 'MID')]
    for _ in range(home_goals):
        scorer = random.choice(att_home)['name'] if att_home else '?'
        events.append({
            'minute': rand_minute(),
            'type': 'goal',
            'player': scorer,
            'team': home_name,
            'emoji': '⚽'
        })

    # گل‌های مهمان
    att_away = [p for p in away_players if p.get('position') in ('ATT', 'MID')]
    for _ in range(away_goals):
        scorer = random.choice(att_away)['name'] if att_away else '?'
        events.append({
            'minute': rand_minute(),
            'type': 'goal',
            'player': scorer,
            'team': away_name,
            'emoji': '⚽'
        })

    # کارت‌های زرد (۱–۴ تا)
    all_outfield = [p for p in home_players + away_players
                    if p.get('position') != 'GK']
    num_yellows = random.randint(1, 4)
    for _ in range(num_yellows):
        if all_outfield:
            carded = random.choice(all_outfield)
            team = home_name if carded in home_players else away_name
            events.append({
                'minute': rand_minute(),
                'type': 'yellow_card',
                'player': carded['name'],
                'team': team,
                'emoji': '🟨'
            })

    events.sort(key=lambda e: e['minute'])
    return events


def format_match_result(result: dict, home_name: str, away_name: str) -> str:
    """فرمت پیام تلگرام برای نتیجه بازی"""
    hg = result['home_goals']
    ag = result['away_goals']

    lines = [
        f"⚽ *{home_name}  {hg} — {ag}  {away_name}*",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    for ev in result['events']:
        lines.append(f"{ev['emoji']} {ev['minute']}' {ev['player']} _({ev['team']})_")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(
        f"📊 Possession: {result['possession_home']}% — {result['possession_away']}%\n"
        f"🎯 Shots: {result['shots_home']} — {result['shots_away']}"
    )
    return "\n".join(lines)
