"""Scheduler for the daily game cycle."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from bengala.bot import BengalaBot

logger = logging.getLogger("bengala")


def setup_scheduler(bot: BengalaBot) -> AsyncIOScheduler:
    """Configure and return the APScheduler for the 06:00 UTC daily cycle."""
    from bengala.bot import run_daily_cycle

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_daily_cycle,
        CronTrigger(hour=6, minute=0, timezone="UTC"),
        args=[bot],
        id="daily_cycle",
        name="Ciclo diário do jogo às 06h00 UTC",
        replace_existing=True,
    )
    return scheduler
