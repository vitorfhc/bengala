"""Tests for bot event handlers and commands."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bengala.bot import BengalaBot, _build_bengalado_nick, run_daily_cycle
from bengala.config import Config
from bengala.db.repository import Repository


def _make_config() -> Config:
    return Config(
        discord_token="test-token",
        watched_channel_id=111,
        admin_role_id=333,
    )


class TestBuildBengaladoNick:
    def test_short_name_unchanged(self) -> None:
        assert _build_bengalado_nick("alice") == "🤡 alice - bengalado"

    def test_long_name_truncated_to_fit_32_chars(self) -> None:
        long_name = "a" * 50
        result = _build_bengalado_nick(long_name)
        assert len(result) <= 32
        assert result.startswith("🤡 ")
        assert result.endswith(" - bengalado")


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

    async def test_renames_on_forbidden_word(self, repo: Repository) -> None:
        config = _make_config()
        bot = BengalaBot(config, repo)
        bot.process_commands = AsyncMock()  # type: ignore[method-assign]

        now = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)
        await repo.create_round("abacaxi", now)

        member = MagicMock()
        member.nick = "alice-nick"
        member.display_name = "alice"
        member.edit = AsyncMock()

        guild = MagicMock()
        guild.get_member = MagicMock(return_value=member)

        message = MagicMock()
        message.author.bot = False
        message.author.id = 100
        message.author.display_name = "alice"
        message.author.send = AsyncMock()
        message.channel.id = 111
        message.content = "eu gosto de abacaxi"
        message.guild = guild

        await bot.on_message(message)

        member.edit.assert_called_once_with(nick="🤡 alice - bengalado")
        message.author.send.assert_called_once()

        active = await repo.get_active_round()
        assert active is not None
        players = await repo.get_round_players(active.id)
        assert len(players) == 1
        assert players[0].muted_at is not None
        assert players[0].original_nickname == "alice-nick"

    async def test_already_punished_sends_taunt(self, repo: Repository) -> None:
        config = _make_config()
        bot = BengalaBot(config, repo)
        bot.process_commands = AsyncMock()  # type: ignore[method-assign]

        now = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)
        round_data = await repo.create_round("abacaxi", now)
        player = await repo.get_or_create_player(round_data.id, 100, "alice")
        await repo.mute_player(player.id, now, "alice-nick")

        member = MagicMock()
        member.nick = "🤡 alice - bengalado"
        member.display_name = "🤡 alice - bengalado"
        member.edit = AsyncMock()

        guild = MagicMock()
        guild.get_member = MagicMock(return_value=member)

        message = MagicMock()
        message.author.bot = False
        message.author.id = 100
        message.author.display_name = "🤡 alice - bengalado"
        message.author.send = AsyncMock()
        message.channel.id = 111
        message.content = "abacaxi de novo"
        message.guild = guild

        await bot.on_message(message)

        member.edit.assert_not_called()
        message.author.send.assert_called_once()


@pytest.mark.asyncio
class TestRunDailyCycle:
    async def test_cycle_with_no_active_round(self, repo: Repository) -> None:
        config = _make_config()
        bot = BengalaBot(config, repo)

        channel = AsyncMock()
        channel.guild = MagicMock()

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

    async def test_cycle_restores_punished_nicknames(
        self, repo: Repository
    ) -> None:
        config = _make_config()
        bot = BengalaBot(config, repo)

        now = datetime(2025, 1, 1, 6, 0, tzinfo=timezone.utc)
        round_data = await repo.create_round("abacaxi", now)
        p1 = await repo.get_or_create_player(round_data.id, 100, "alice")
        p2 = await repo.get_or_create_player(round_data.id, 101, "bob")
        await repo.mute_player(p1.id, now, "alice-nick")
        await repo.mute_player(p2.id, now, None)

        alice_member = MagicMock()
        alice_member.edit = AsyncMock()
        bob_member = MagicMock()
        bob_member.edit = AsyncMock()

        def get_member(user_id: int) -> object:
            return {100: alice_member, 101: bob_member}.get(user_id)

        guild = MagicMock()
        guild.get_member = MagicMock(side_effect=get_member)

        channel = AsyncMock()
        channel.guild = guild
        channel.send = AsyncMock()

        async def async_gen() -> object:
            return
            yield  # noqa: unreachable

        channel.history = MagicMock(return_value=async_gen())

        bot.get_channel = MagicMock(return_value=channel)  # type: ignore[method-assign]
        channel.__class__ = type("TextChannel", (), {})

        with patch("bengala.bot.isinstance", return_value=True):
            with patch("bengala.bot.select_forbidden_word", return_value="banana"):
                await run_daily_cycle(bot)

        alice_member.edit.assert_awaited_once_with(nick="alice-nick")
        bob_member.edit.assert_awaited_once_with(nick=None)

        active = await repo.get_active_round()
        assert active is not None
        assert active.forbidden_word == "banana"
