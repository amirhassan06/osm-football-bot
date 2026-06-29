#!/usr/bin/env python3
"""
اجرا: python3 scripts/csv_to_sql.py data/players_template.csv > migrations/0002_seed.sql
بعد: wrangler d1 execute osm_football --file=migrations/0002_seed.sql
"""

import csv
import sys
import math

def player_value(rating, age):
    """محاسبه ارزش بازیکن بر اساس رتبه و سن"""
    peak_age = 27
    age_factor = max(0.3, 1 - abs(age - peak_age) * 0.035)
    return int(rating ** 2 * age_factor * 1500)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 csv_to_sql.py <players.csv>", file=sys.stderr)
        sys.exit(1)

    csv_file = sys.argv[1]

    leagues = {}    # name -> id
    clubs   = {}    # name -> {id, league_id}
    league_counter = 1
    club_counter   = 1

    rows = []
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    # جمع‌آوری leagues و clubs
    for row in rows:
        ln = row['league_name'].strip()
        cn = row['club_name'].strip()
        lc = row['league_country'].strip()

        if ln not in leagues:
            leagues[ln] = {'id': league_counter, 'country': lc}
            league_counter += 1

        if cn not in clubs:
            clubs[cn] = {'id': club_counter, 'league_id': leagues[ln]['id']}
            club_counter += 1

    print("-- Auto-generated seed SQL")
    print("-- DO NOT EDIT MANUALLY\n")

    # Leagues
    print("-- Leagues")
    for name, data in leagues.items():
        safe_name = name.replace("'", "''")
        safe_country = data['country'].replace("'", "''")
        print(f"INSERT OR IGNORE INTO leagues (id, name, country, total_rounds) "
              f"VALUES ({data['id']}, '{safe_name}', '{safe_country}', 10);")

    print()

    # Clubs
    print("-- Clubs")
    for name, data in clubs.items():
        safe_name = name.replace("'", "''")
        short = name[:3].upper()
        print(f"INSERT OR IGNORE INTO clubs (id, name, short_name, league_id, budget) "
              f"VALUES ({data['id']}, '{safe_name}', '{short}', {data['league_id']}, 10000000);")

    print()

    # Standings init (یک ردیف برای هر club در هر league)
    print("-- Standings (initial)")
    standing_id = 1
    for name, data in clubs.items():
        print(f"INSERT OR IGNORE INTO standings (id, league_id, club_id) "
              f"VALUES ({standing_id}, {data['league_id']}, {data['id']});")
        standing_id += 1

    print()

    # Players
    print("-- Players")
    for i, row in enumerate(rows, start=1):
        name    = row['name'].strip().replace("'", "''")
        pos     = row['position'].strip()
        rating  = float(row['rating'])
        age     = int(row['age'])
        club_id = clubs[row['club_name'].strip()]['id']
        value   = player_value(rating, age)

        print(f"INSERT OR IGNORE INTO players (id, name, position, rating, age, stamina, club_id, value) "
              f"VALUES ({i}, '{name}', '{pos}', {rating}, {age}, 100, {club_id}, {value});")

    print()

    # Fixtures (round-robin برای هر league)
    print("-- Fixtures")
    match_id = 1
    for league_name, league_data in leagues.items():
        lid = league_data['id']
        league_clubs = [cid for cname, cdata in clubs.items()
                        if cdata['league_id'] == lid
                        for cid in [cdata['id']]]

        # ساده‌ترین روش: هر جفت یک بار (home/away)
        fixtures = []
        n = len(league_clubs)
        for i in range(n):
            for j in range(i+1, n):
                fixtures.append((league_clubs[i], league_clubs[j]))

        # پخش روی rounds
        rounds = min(10, len(fixtures))
        per_round = max(1, len(fixtures) // rounds)

        for r in range(1, rounds + 1):
            start = (r-1) * per_round
            end   = start + per_round
            for home, away in fixtures[start:end]:
                print(f"INSERT OR IGNORE INTO matches (id, league_id, round_num, home_club_id, away_club_id) "
                      f"VALUES ({match_id}, {lid}, {r}, {home}, {away});")
                match_id += 1

    print("\n-- Seed complete")

if __name__ == '__main__':
    main()
