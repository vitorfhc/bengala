"""Tests for scheduler setup."""

from __future__ import annotations

from unittest.mock import MagicMock

from bengala.scheduler import setup_scheduler


class TestSetupScheduler:
    def test_creates_scheduler_with_daily_job(self) -> None:
        bot = MagicMock()
        scheduler = setup_scheduler(bot)

        jobs = scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "daily_cycle"
