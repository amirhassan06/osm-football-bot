-- migrations/0001_init.sql
-- اجرا: wrangler d1 execute osm_football --file=migrations/0001_init.sql

CREATE TABLE IF NOT EXISTS managers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username    TEXT,
    name        TEXT,
    club_id     INTEGER,
    manager_points INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS leagues (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    country     TEXT,
    season      TEXT DEFAULT '2025-26',
    current_round INTEGER DEFAULT 0,
    total_rounds  INTEGER DEFAULT 10
);

CREATE TABLE IF NOT EXISTS clubs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    short_name  TEXT,
    league_id   INTEGER NOT NULL,
    budget      REAL DEFAULT 10000000,
    stadium_cap INTEGER DEFAULT 30000,
    manager_id  INTEGER,         -- NULL = AI مدیریت می‌کند
    tactic_formation TEXT DEFAULT '4-4-2',
    tactic_style     TEXT DEFAULT 'balanced',
    FOREIGN KEY (league_id) REFERENCES leagues(id)
);

CREATE TABLE IF NOT EXISTS players (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    position    TEXT NOT NULL,   -- GK, DEF, MID, ATT
    rating      REAL NOT NULL,
    age         INTEGER NOT NULL,
    stamina     REAL DEFAULT 100,
    club_id     INTEGER,
    value       REAL,            -- محاسبه از rating/age
    for_sale    INTEGER DEFAULT 0,
    FOREIGN KEY (club_id) REFERENCES clubs(id)
);

CREATE TABLE IF NOT EXISTS matches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id   INTEGER NOT NULL,
    round_num   INTEGER NOT NULL,
    home_club_id INTEGER NOT NULL,
    away_club_id INTEGER NOT NULL,
    home_goals  INTEGER,
    away_goals  INTEGER,
    events_json TEXT,            -- JSON آرایه رویدادها
    played      INTEGER DEFAULT 0,
    FOREIGN KEY (league_id) REFERENCES leagues(id)
);

CREATE TABLE IF NOT EXISTS standings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id   INTEGER NOT NULL,
    club_id     INTEGER NOT NULL,
    played      INTEGER DEFAULT 0,
    wins        INTEGER DEFAULT 0,
    draws       INTEGER DEFAULT 0,
    losses      INTEGER DEFAULT 0,
    goals_for   INTEGER DEFAULT 0,
    goals_against INTEGER DEFAULT 0,
    points      INTEGER DEFAULT 0,
    UNIQUE(league_id, club_id)
);

CREATE TABLE IF NOT EXISTS transfers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id   INTEGER NOT NULL,
    from_club_id INTEGER,
    to_club_id  INTEGER,
    fee         REAL,
    status      TEXT DEFAULT 'pending',  -- pending, accepted, rejected
    offered_by  INTEGER,                 -- manager telegram_id
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS training_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id     INTEGER NOT NULL,
    player_id   INTEGER NOT NULL,
    rating_boost REAL,
    stamina_boost REAL,
    trained_at  TEXT DEFAULT (datetime('now'))
);

-- ایندکس‌های مهم
CREATE INDEX IF NOT EXISTS idx_players_club ON players(club_id);
CREATE INDEX IF NOT EXISTS idx_matches_league_round ON matches(league_id, round_num);
CREATE INDEX IF NOT EXISTS idx_standings_league ON standings(league_id, points DESC);
CREATE INDEX IF NOT EXISTS idx_clubs_manager ON clubs(manager_id);
