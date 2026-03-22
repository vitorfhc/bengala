"""Discord bot setup with event handlers and slash commands."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import cast

import discord
from discord import app_commands
from discord.ext import commands

from apscheduler.triggers.date import DateTrigger  # type: ignore[import-untyped]

from bengala.config import Config
from bengala.db.repository import Repository
from bengala.messages import (
    format_already_muted_notice,
    format_final_scoreboard,
    format_mute_notice,
    format_no_active_round,
    format_no_permission,
    format_partial_scoreboard,
    format_restart_confirmation,
    format_rules,
    format_secret_word,
)
from bengala.scoring import build_scoreboard
from bengala.word_pipeline import contains_forbidden_word, select_forbidden_word

logger = logging.getLogger("bengala")


class BengalaBot(commands.Bot):
    """The Bengala Discord bot."""

    def __init__(self, config: Config, repo: Repository) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.config = config
        self.repo = repo

    async def setup_hook(self) -> None:
        """Called when the bot is starting up."""
        self.tree.add_command(_rules_command)
        self.tree.add_command(_placar_command)
        self.tree.add_command(_secret_command)
        self.tree.add_command(_restart_command)
        self.tree.add_command(_reroll_command)

        # Sync to the watched channel's guild for instant availability
        try:
            channel = await self.fetch_channel(self.config.watched_channel_id)
            if hasattr(channel, "guild"):
                guild_id = channel.guild.id  # type: ignore[union-attr,unused-ignore]
                guild = discord.Object(id=guild_id)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                # Clear stale global commands to avoid duplicates
                self.tree.clear_commands(guild=None)
                await self.tree.sync()
                logger.info("Slash commands synced to guild %s.", guild_id)
                return
        except Exception:
            logger.warning("Não foi possível buscar o canal — sync global.")

        await self.tree.sync()
        logger.info("Slash commands synced globally.")

    async def on_ready(self) -> None:
        """Called when the bot is connected and ready."""
        logger.info("Bengala bot online como %s", self.user)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Send rules when bot joins a new server."""
        channel = guild.get_channel(self.config.watched_channel_id)
        if channel is not None and isinstance(channel, discord.TextChannel):
            await channel.send(format_rules())
        else:
            logger.warning(
                "Canal %d não encontrado no servidor %s",
                self.config.watched_channel_id,
                guild.name,
            )

    async def on_message(self, message: discord.Message) -> None:
        """Monitor messages for the forbidden word."""
        if message.author.bot:
            return
        if message.channel.id != self.config.watched_channel_id:
            return

        active_round = await self.repo.get_active_round()
        if active_round is None:
            return

        now = datetime.now(timezone.utc)
        player = await self.repo.get_or_create_player(
            active_round.id,
            message.author.id,
            message.author.display_name,
        )

        await self.repo.add_message(
            active_round.id, player.id, message.content, now
        )

        if contains_forbidden_word(message.content, active_round.forbidden_word):
            guild = message.guild
            if guild is None:
                return

            member = guild.get_member(message.author.id)
            if member is None:
                return

            mute_role = guild.get_role(self.config.mute_role_id)
            if mute_role is None:
                logger.error("Cargo de mute %d não encontrado!", self.config.mute_role_id)
                return

            if mute_role in member.roles:
                # Already muted — send taunt
                try:
                    await message.author.send(format_already_muted_notice())
                except discord.Forbidden:
                    logger.warning("Não foi possível enviar DM para %s", message.author)
            else:
                # Mute the player
                await member.add_roles(mute_role)
                await self.repo.mute_player(player.id, now)
                player.muted_at = now
                # Schedule automatic unmute after 1 hour
                self.scheduler.add_job(
                    unmute_player,
                    DateTrigger(run_date=now + timedelta(hours=1)),
                    args=[self, guild.id, member.id, mute_role.id],
                    id=f"unmute_{member.id}_{active_round.id}",
                    replace_existing=True,
                )
                try:
                    await message.author.send(format_mute_notice())
                except discord.Forbidden:
                    logger.warning("Não foi possível enviar DM para %s", message.author)

        if "padi" in message.content.lower().split():
            try:
                await message.author.send(
                    "padi, o comedor de tomboy do server"
                )
            except discord.Forbidden:
                logger.warning("Não foi possível enviar DM para %s", message.author)

        await self.process_commands(message)


async def unmute_player(
    bot: BengalaBot, guild_id: int, member_id: int, mute_role_id: int
) -> None:
    """Remove the mute role from a player after the mute duration expires."""
    guild = bot.get_guild(guild_id)
    if guild is None:
        return
    member = guild.get_member(member_id)
    if member is None:
        return
    mute_role = guild.get_role(mute_role_id)
    if mute_role is None or mute_role not in member.roles:
        return
    try:
        await member.remove_roles(mute_role)
        logger.info("Mute expirado para %s", member)
    except discord.Forbidden:
        logger.warning("Não foi possível remover mute de %s", member)


async def _compute_scoreboard(
    repo: Repository, round_id: int
) -> tuple[list[object], dict[int, list[object]]]:
    """Compute scoreboard data for a round."""
    players = await repo.get_round_players(round_id)
    messages_by_player = await repo.get_all_player_messages_for_round(round_id)
    scores = build_scoreboard(players, messages_by_player)
    return scores, messages_by_player  # type: ignore[return-value]


async def run_daily_cycle(bot: BengalaBot) -> None:
    """Execute the daily cycle: scoreboard, unmute, select word, new round."""
    now = datetime.now(timezone.utc)
    repo = bot.repo
    config = bot.config

    channel = bot.get_channel(config.watched_channel_id)
    if channel is None or not isinstance(channel, discord.TextChannel):
        logger.error("Canal monitorado %d não encontrado!", config.watched_channel_id)
        return

    # 1. Send final scoreboard if there's an active round
    active_round = await repo.get_active_round()
    if active_round is not None:
        players = await repo.get_round_players(active_round.id)
        messages_by_player = await repo.get_all_player_messages_for_round(
            active_round.id
        )
        scores = build_scoreboard(players, messages_by_player)
        scoreboard_msg = format_final_scoreboard(
            active_round.forbidden_word, scores
        )
        await channel.send(scoreboard_msg)
        await repo.end_round(active_round.id, now)

    # 2. Remove mute role from all members
    guild = channel.guild
    mute_role = guild.get_role(config.mute_role_id)
    if mute_role is not None:
        for member in mute_role.members:
            try:
                await member.remove_roles(mute_role)
            except discord.Forbidden:
                logger.warning("Não foi possível remover mute de %s", member)

    # 3. Select new forbidden word
    seven_days_ago = now - timedelta(days=7)
    raw_messages: list[str] = []
    try:
        async for msg in channel.history(after=seven_days_ago, limit=10000):
            if not msg.author.bot:
                raw_messages.append(msg.content)
    except discord.DiscordServerError:
        logger.warning("Erro ao buscar histórico de mensagens — usando fallback")

    forbidden_word = select_forbidden_word(raw_messages)

    # 4. Start new round
    await repo.create_round(forbidden_word, now)
    logger.info("Nova rodada iniciada. Palavra proibida: %s", forbidden_word)


def _get_bot(interaction: discord.Interaction) -> BengalaBot:
    """Get the BengalaBot instance from an interaction."""
    return cast(BengalaBot, interaction.client)


def _has_admin_role(interaction: discord.Interaction, admin_role_id: int) -> bool:
    """Check if the interaction user has the admin role."""
    if interaction.guild is None:
        return False
    member = interaction.guild.get_member(interaction.user.id)
    if member is None:
        return False
    return any(role.id == admin_role_id for role in member.roles)


@app_commands.command(name="rules", description="Exibe as regras do jogo Bengala")
async def _rules_command(interaction: discord.Interaction) -> None:
    """Show game rules."""
    await interaction.response.send_message(format_rules())


@app_commands.command(
    name="placar", description="Mostra o placar parcial da rodada atual"
)
async def _placar_command(interaction: discord.Interaction) -> None:
    """Show partial scoreboard."""
    bot = _get_bot(interaction)
    active_round = await bot.repo.get_active_round()

    if active_round is None:
        await interaction.response.send_message(format_no_active_round())
        return

    players = await bot.repo.get_round_players(active_round.id)
    messages_by_player = await bot.repo.get_all_player_messages_for_round(
        active_round.id
    )
    scores = build_scoreboard(players, messages_by_player)
    await interaction.response.send_message(format_partial_scoreboard(scores))


@app_commands.command(
    name="secret", description="Revela a palavra proibida (apenas admins)"
)
async def _secret_command(interaction: discord.Interaction) -> None:
    """Reveal the secret word (admin only, ephemeral)."""
    bot = _get_bot(interaction)

    if not _has_admin_role(interaction, bot.config.admin_role_id):
        await interaction.response.send_message(
            format_no_permission(), ephemeral=True
        )
        return

    active_round = await bot.repo.get_active_round()
    if active_round is None:
        await interaction.response.send_message(
            format_no_active_round(), ephemeral=True
        )
        return

    await interaction.response.send_message(
        format_secret_word(active_round.forbidden_word), ephemeral=True
    )


@app_commands.command(
    name="restart", description="Reinicia o jogo imediatamente (apenas admins)"
)
async def _restart_command(interaction: discord.Interaction) -> None:
    """Force restart the game (admin only)."""
    bot = _get_bot(interaction)

    if not _has_admin_role(interaction, bot.config.admin_role_id):
        await interaction.response.send_message(
            format_no_permission(), ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    await run_daily_cycle(bot)
    await interaction.followup.send(format_restart_confirmation(), ephemeral=True)


@app_commands.command(
    name="reroll", description="Sorteia uma nova palavra proibida sem reiniciar a rodada"
)
async def _reroll_command(interaction: discord.Interaction) -> None:
    """Reroll the forbidden word without creating a new round (admin only)."""
    bot = _get_bot(interaction)

    if not _has_admin_role(interaction, bot.config.admin_role_id):
        await interaction.response.send_message(
            format_no_permission(), ephemeral=True
        )
        return

    active_round = await bot.repo.get_active_round()
    if active_round is None:
        await interaction.response.send_message(
            format_no_active_round(), ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    channel = bot.get_channel(bot.config.watched_channel_id)
    if channel is not None and isinstance(channel, discord.TextChannel):
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        raw_messages: list[str] = []
        try:
            async for msg in channel.history(after=seven_days_ago, limit=10000):
                if not msg.author.bot:
                    raw_messages.append(msg.content)
        except discord.DiscordServerError:
            logger.warning("Erro ao buscar histórico — usando fallback")

        new_word = select_forbidden_word(raw_messages)
    else:
        new_word = select_forbidden_word([])

    await bot.repo.update_forbidden_word(active_round.id, new_word)
    logger.info("Reroll: nova palavra proibida: %s", new_word)
    await interaction.followup.send(
        f'🎲 Nova palavra proibida sorteada: **"{new_word}"**. '
        f"A rodada continua normalmente.",
        ephemeral=True,
    )
