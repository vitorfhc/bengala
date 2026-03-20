"""Tests for bot event handlers and commands."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bengala.bot import BengalaBot, run_daily_cycle
from bengala.config import Config
from bengala.db.repository import Repository


def _make_config() -> Config:
    return Config(
        discord_token="test-token",
        watched_channel_id=111,
        mute_role_id=222,
        admin_role_id=333,
    )


@pytest.mark.asyncio
class TestOnMessage:
    async def test_ignores_bot_messages(self, repo: Repository) -> None:
        config = _make_config()
        bot = BengalaBot(config, repo)

        message = MagicMock()
        message.author.bot = True
        message.channel.id = 111

        await bot.on_message(message)
        # No interaction with repo expected

    async def test_ignores_wrong_channel(self, repo: Repository) -> None:
        config = _make_config()
        bot = BengalaBot(config, repo)

        message = MagicMock()
        message.author.bot = False
        message.channel.id = 999  # wrong channel

        await bot.on_message(message)

    async def test_registers_player_and_message(self, repo: Repository) -> None:
        config = _make_config()
        bot = BengalaBot(config, repo)
        bot.process_commands = AsyncMock()  # type: ignore[method-assign]

        now = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)
        await repo.create_round("abacaxi", now)

        message = MagicMock()
        message.author.bot = False
        message.author.id = 100
        message.author.display_name = "alice"
        message.channel.id = 111
        message.content = "olá pessoal tudo bem"
        message.guild = None  # simplified

        await bot.on_message(message)

        active = await repo.get_active_round()
        assert active is not None
        players = await repo.get_round_players(active.id)
        assert len(players) == 1
        assert players[0].username == "alice"

    async def test_mutes_on_forbidden_word(self, repo: Repository) -> None:
        config = _make_config()
        bot = BengalaBot(config, repo)
        bot.process_commands = AsyncMock()  # type: ignore[method-assign]

        now = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)
        await repo.create_round("abacaxi", now)

        mute_role = MagicMock()
        mute_role.id = 222
        mute_role.members = []

        member = MagicMock()
        member.roles = []
        member.add_roles = AsyncMock()

        guild = MagicMock()
        guild.get_member = MagicMock(return_value=member)
        guild.get_role = MagicMock(return_value=mute_role)

        message = MagicMock()
        message.author.bot = False
        message.author.id = 100
        message.author.display_name = "alice"
        message.author.send = AsyncMock()
        message.channel.id = 111
        message.content = "eu gosto de abacaxi"
        message.guild = guild

        await bot.on_message(message)

        member.add_roles.assert_called_once_with(mute_role)
        message.author.send.assert_called_once()


@pytest.mark.asyncio
class TestRunDailyCycle:
    async def test_cycle_with_no_active_round(self, repo: Repository) -> None:
        config = _make_config()
        bot = BengalaBot(config, repo)

        channel = AsyncMock()
        channel.guild = MagicMock()
        channel.guild.get_role = MagicMock(return_value=None)

        async def mock_history(**kwargs: object) -> list[MagicMock]:
            return []

        # Use async generator for history
        async def async_gen() -> object:
            return
            yield  # noqa: unreachable

        channel.history = MagicMock(return_value=async_gen())
        channel.send = AsyncMock()

        bot.get_channel = MagicMock(return_value=channel)  # type: ignore[method-assign]
        # Simulate isinstance check
        channel.__class__ = type("TextChannel", (), {})

        with patch("bengala.bot.isinstance", return_value=True):
            with patch("bengala.bot.select_forbidden_word", return_value="teste"):
                await run_daily_cycle(bot)

        # Should have created a new round
        active = await repo.get_active_round()
        assert active is not None
        assert active.forbidden_word == "teste"
