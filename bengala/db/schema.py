"""Database schema initialization."""

from __future__ import annotations

import aiosqlite

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS rounds (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    forbidden_word TEXT    NOT NULL,
    started_at     TEXT    NOT NULL,
    ended_at       TEXT
);

CREATE TABLE IF NOT EXISTS players (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id          INTEGER NOT NULL REFERENCES rounds(id),
    user_id           INTEGER NOT NULL,
    username          TEXT    NOT NULL,
    muted_at          TEXT,
    original_nickname TEXT,
    UNIQUE(round_id, user_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id  INTEGER NOT NULL REFERENCES rounds(id),
    player_id INTEGER NOT NULL REFERENCES players(id),
    content   TEXT    NOT NULL,
    sent_at   TEXT    NOT NULL
);
"""


async def _ensure_original_nickname_column(conn: aiosqlite.Connection) -> None:
    """Add original_nickname column to players for pre-existing databases."""
    async with conn.execute("PRAGMA table_info(players)") as cursor:
        columns = {row[1] for row in await cursor.fetchall()}
    if "original_nickname" not in columns:
        await conn.execute("ALTER TABLE players ADD COLUMN original_nickname TEXT")


async def init_db(db_path: str) -> aiosqlite.Connection:
    """Initialize the database and return a connection."""
    conn = await aiosqlite.connect(db_path)
    await conn.executescript(SCHEMA_SQL)
    await _ensure_original_nickname_column(conn)
    await conn.commit()
    return conn
