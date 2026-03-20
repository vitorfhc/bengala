"""Data models for the Bengala bot."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RoundData:
    """Represents a game round."""

    id: int
    forbidden_word: str
    started_at: datetime
    ended_at: datetime | None = None


@dataclass
class PlayerData:
    """Represents a player in a round."""

    id: int
    round_id: int
    user_id: int
    username: str
    muted_at: datetime | None = None


@dataclass
class MessageData:
    """Represents a message sent by a player."""

    id: int
    round_id: int
    player_id: int
    content: str
    sent_at: datetime


@dataclass
class PlayerScore:
    """Represents a player's score for display."""

    user_id: int
    username: str
    score: int
    muted: bool = False


@dataclass
class RoundState:
    """In-memory state for the active round."""

    round_id: int
    forbidden_word: str
    started_at: datetime
    players: dict[int, PlayerData] = field(default_factory=dict)
