"""Entry point for the Bengala bot: python -m bengala."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

import nltk  # type: ignore[import-untyped]

from bengala.bot import BengalaBot
from bengala.config import load_config
from bengala.db.repository import Repository
from bengala.db.schema import init_db
from bengala.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bengala")


async def main() -> None:
    """Initialize and run the bot."""
    try:
        config = load_config()
    except ValueError as exc:
        logger.error("Erro de configuração: %s", exc)
        sys.exit(1)

    # Ensure NLTK stopwords are available
    nltk.download("stopwords", quiet=True)

    # Initialize database
    db_path = os.environ.get("BENGALA_DB_PATH", "data/bengala.db")
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = await init_db(db_path)
    repo = Repository(conn)

    # Create and run bot
    bot = BengalaBot(config, repo)

    original_setup_hook = bot.setup_hook

    async def setup_hook_with_scheduler() -> None:
        await original_setup_hook()
        scheduler = setup_scheduler(bot)
        scheduler.start()
        logger.info("Scheduler iniciado — ciclo diário às 06h00 UTC")

    bot.setup_hook = setup_hook_with_scheduler  # type: ignore[method-assign]

    async with bot:
        await bot.start(config.discord_token)


if __name__ == "__main__":
    asyncio.run(main())
