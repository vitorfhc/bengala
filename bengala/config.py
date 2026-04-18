"""Configuration loading from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Bot configuration loaded from environment variables."""

    discord_token: str
    watched_channel_id: int
    admin_role_id: int


def load_config() -> Config:
    """Load and validate configuration from environment variables.

    Raises:
        ValueError: If any required variable is missing or invalid.
    """
    missing: list[str] = []
    for var in ("DISCORD_TOKEN", "WATCHED_CHANNEL_ID", "ADMIN_ROLE_ID"):
        if not os.environ.get(var):
            missing.append(var)

    if missing:
        raise ValueError(
            f"Variáveis de ambiente obrigatórias ausentes: {', '.join(missing)}"
        )

    try:
        watched_channel_id = int(os.environ["WATCHED_CHANNEL_ID"])
        admin_role_id = int(os.environ["ADMIN_ROLE_ID"])
    except ValueError as exc:
        raise ValueError(
            "WATCHED_CHANNEL_ID e ADMIN_ROLE_ID devem ser inteiros válidos"
        ) from exc

    return Config(
        discord_token=os.environ["DISCORD_TOKEN"],
        watched_channel_id=watched_channel_id,
        admin_role_id=admin_role_id,
    )
