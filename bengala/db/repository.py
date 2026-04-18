"""Database repository for CRUD operations."""

from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite

from bengala.models import MessageData, PlayerData, RoundData


def _parse_dt(value: str) -> datetime:
    """Parse an ISO 8601 datetime string to a timezone-aware datetime."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _format_dt(dt: datetime) -> str:
    """Format a datetime to ISO 8601 string."""
    return dt.isoformat()


class Repository:
    """Async repository wrapping all SQLite operations."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def create_round(
        self, forbidden_word: str, started_at: datetime
    ) -> RoundData:
        """Create a new round and return it."""
        cursor = await self._conn.execute(
            "INSERT INTO rounds (forbidden_word, started_at) VALUES (?, ?)",
            (forbidden_word, _format_dt(started_at)),
        )
        await self._conn.commit()
        round_id = cursor.lastrowid
        assert round_id is not None
        return RoundData(
            id=round_id,
            forbidden_word=forbidden_word,
            started_at=started_at,
        )

    async def update_forbidden_word(
        self, round_id: int, new_word: str
    ) -> None:
        """Update the forbidden word for an active round."""
        await self._conn.execute(
            "UPDATE rounds SET forbidden_word = ? WHERE id = ?",
            (new_word, round_id),
        )
        await self._conn.commit()

    async def end_round(self, round_id: int, ended_at: datetime) -> None:
        """Mark a round as ended."""
        await self._conn.execute(
            "UPDATE rounds SET ended_at = ? WHERE id = ?",
            (_format_dt(ended_at), round_id),
        )
        await self._conn.commit()

    async def get_active_round(self) -> RoundData | None:
        """Get the currently active round (ended_at IS NULL)."""
        async with self._conn.execute(
            "SELECT id, forbidden_word, started_at, ended_at "
            "FROM rounds WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return RoundData(
                id=row[0],
                forbidden_word=row[1],
                started_at=_parse_dt(row[2]),
                ended_at=None,
            )

    async def get_or_create_player(
        self, round_id: int, user_id: int, username: str
    ) -> PlayerData:
        """Get an existing player or create a new one for this round."""
        async with self._conn.execute(
            "SELECT id, round_id, user_id, username, muted_at, original_nickname "
            "FROM players WHERE round_id = ? AND user_id = ?",
            (round_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
            if row is not None:
                return PlayerData(
                    id=row[0],
                    round_id=row[1],
                    user_id=row[2],
                    username=row[3],
                    muted_at=_parse_dt(row[4]) if row[4] else None,
                    original_nickname=row[5],
                )

        cursor = await self._conn.execute(
            "INSERT INTO players (round_id, user_id, username) VALUES (?, ?, ?)",
            (round_id, user_id, username),
        )
        await self._conn.commit()
        player_id = cursor.lastrowid
        assert player_id is not None
        return PlayerData(
            id=player_id,
            round_id=round_id,
            user_id=user_id,
            username=username,
        )

    async def mute_player(
        self,
        player_id: int,
        muted_at: datetime,
        original_nickname: str | None,
    ) -> None:
        """Record that a player was punished, storing their pre-punishment nick."""
        await self._conn.execute(
            "UPDATE players SET muted_at = ?, original_nickname = ? WHERE id = ?",
            (_format_dt(muted_at), original_nickname, player_id),
        )
        await self._conn.commit()

    async def get_punished_players(
        self, round_id: int
    ) -> list[tuple[int, str | None]]:
        """Get (user_id, original_nickname) for all punished players in a round."""
        async with self._conn.execute(
            "SELECT user_id, original_nickname FROM players "
            "WHERE round_id = ? AND muted_at IS NOT NULL",
            (round_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [(row[0], row[1]) for row in rows]

    async def add_message(
        self,
        round_id: int,
        player_id: int,
        content: str,
        sent_at: datetime,
    ) -> MessageData:
        """Store a player's message."""
        cursor = await self._conn.execute(
            "INSERT INTO messages (round_id, player_id, content, sent_at) "
            "VALUES (?, ?, ?, ?)",
            (round_id, player_id, content, _format_dt(sent_at)),
        )
        await self._conn.commit()
        msg_id = cursor.lastrowid
        assert msg_id is not None
        return MessageData(
            id=msg_id,
            round_id=round_id,
            player_id=player_id,
            content=content,
            sent_at=sent_at,
        )

    async def get_round_players(self, round_id: int) -> list[PlayerData]:
        """Get all players in a round."""
        async with self._conn.execute(
            "SELECT id, round_id, user_id, username, muted_at, original_nickname "
            "FROM players WHERE round_id = ?",
            (round_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                PlayerData(
                    id=row[0],
                    round_id=row[1],
                    user_id=row[2],
                    username=row[3],
                    muted_at=_parse_dt(row[4]) if row[4] else None,
                    original_nickname=row[5],
                )
                for row in rows
            ]

    async def get_player_messages(
        self,
        player_id: int,
        before: datetime | None = None,
    ) -> list[MessageData]:
        """Get all messages for a player, optionally before a timestamp."""
        if before is not None:
            query = (
                "SELECT id, round_id, player_id, content, sent_at "
                "FROM messages WHERE player_id = ? AND sent_at < ? "
                "ORDER BY sent_at"
            )
            params: tuple[int | str, ...] = (player_id, _format_dt(before))
        else:
            query = (
                "SELECT id, round_id, player_id, content, sent_at "
                "FROM messages WHERE player_id = ? ORDER BY sent_at"
            )
            params = (player_id,)

        async with self._conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [
                MessageData(
                    id=row[0],
                    round_id=row[1],
                    player_id=row[2],
                    content=row[3],
                    sent_at=_parse_dt(row[4]),
                )
                for row in rows
            ]

    async def get_all_player_messages_for_round(
        self, round_id: int
    ) -> dict[int, list[MessageData]]:
        """Get all messages grouped by player_id for a round."""
        async with self._conn.execute(
            "SELECT id, round_id, player_id, content, sent_at "
            "FROM messages WHERE round_id = ? ORDER BY sent_at",
            (round_id,),
        ) as cursor:
            rows = await cursor.fetchall()

        result: dict[int, list[MessageData]] = {}
        for row in rows:
            msg = MessageData(
                id=row[0],
                round_id=row[1],
                player_id=row[2],
                content=row[3],
                sent_at=_parse_dt(row[4]),
            )
            result.setdefault(msg.player_id, []).append(msg)
        return result
