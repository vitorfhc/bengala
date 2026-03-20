"""Tests for the database repository."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from bengala.db.repository import Repository


@pytest.mark.asyncio
class TestRepository:
    async def test_create_and_get_round(self, repo: Repository) -> None:
        now = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)
        round_data = await repo.create_round("abacaxi", now)
        assert round_data.forbidden_word == "abacaxi"
        assert round_data.started_at == now

        active = await repo.get_active_round()
        assert active is not None
        assert active.id == round_data.id

    async def test_end_round(self, repo: Repository) -> None:
        now = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)
        round_data = await repo.create_round("abacaxi", now)
        end = datetime(2025, 1, 2, 6, 0, tzinfo=timezone.utc)
        await repo.end_round(round_data.id, end)

        active = await repo.get_active_round()
        assert active is None

    async def test_get_or_create_player(self, repo: Repository) -> None:
        now = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)
        round_data = await repo.create_round("abacaxi", now)

        player1 = await repo.get_or_create_player(round_data.id, 100, "alice")
        player2 = await repo.get_or_create_player(round_data.id, 100, "alice")
        assert player1.id == player2.id  # same player

        player3 = await repo.get_or_create_player(round_data.id, 101, "bob")
        assert player3.id != player1.id

    async def test_mute_player(self, repo: Repository) -> None:
        now = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)
        round_data = await repo.create_round("abacaxi", now)
        player = await repo.get_or_create_player(round_data.id, 100, "alice")
        assert player.muted_at is None

        mute_time = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        await repo.mute_player(player.id, mute_time)

        # Re-fetch
        player2 = await repo.get_or_create_player(round_data.id, 100, "alice")
        assert player2.muted_at == mute_time

    async def test_add_and_get_messages(self, repo: Repository) -> None:
        now = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)
        round_data = await repo.create_round("abacaxi", now)
        player = await repo.get_or_create_player(round_data.id, 100, "alice")

        msg_time = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        await repo.add_message(round_data.id, player.id, "olá mundo", msg_time)

        messages = await repo.get_player_messages(player.id)
        assert len(messages) == 1
        assert messages[0].content == "olá mundo"

    async def test_get_player_messages_before(self, repo: Repository) -> None:
        now = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)
        round_data = await repo.create_round("abacaxi", now)
        player = await repo.get_or_create_player(round_data.id, 100, "alice")

        t1 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc)
        await repo.add_message(round_data.id, player.id, "primeira", t1)
        await repo.add_message(round_data.id, player.id, "segunda", t2)

        cutoff = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        messages = await repo.get_player_messages(player.id, before=cutoff)
        assert len(messages) == 1
        assert messages[0].content == "primeira"

    async def test_get_all_player_messages_for_round(
        self, repo: Repository
    ) -> None:
        now = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)
        round_data = await repo.create_round("abacaxi", now)
        p1 = await repo.get_or_create_player(round_data.id, 100, "alice")
        p2 = await repo.get_or_create_player(round_data.id, 101, "bob")

        t1 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        await repo.add_message(round_data.id, p1.id, "msg1", t1)
        await repo.add_message(round_data.id, p2.id, "msg2", t1)

        result = await repo.get_all_player_messages_for_round(round_data.id)
        assert p1.id in result
        assert p2.id in result
        assert len(result[p1.id]) == 1
        assert len(result[p2.id]) == 1
