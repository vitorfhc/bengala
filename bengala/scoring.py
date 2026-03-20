"""Scoring logic for the Bengala game."""

from __future__ import annotations

from datetime import datetime

from bengala.models import MessageData, PlayerData, PlayerScore
from bengala.word_pipeline import filter_tokens, tokenize_message


def calculate_player_score(
    player: PlayerData,
    messages: list[MessageData],
) -> PlayerScore:
    """Calculate score for a single player.

    For muted players, only messages sent before mute timestamp are counted.
    Score = number of unique words after tokenization, stop-word removal, and dedup.
    """
    relevant_messages: list[MessageData]
    if player.muted_at is not None:
        relevant_messages = [m for m in messages if m.sent_at < player.muted_at]
    else:
        relevant_messages = messages

    all_tokens: list[str] = []
    for msg in relevant_messages:
        all_tokens.extend(tokenize_message(msg.content))

    unique_words = filter_tokens(all_tokens)

    return PlayerScore(
        user_id=player.user_id,
        username=player.username,
        score=len(unique_words),
        muted=player.muted_at is not None,
    )


def build_scoreboard(
    players: list[PlayerData],
    messages_by_player: dict[int, list[MessageData]],
) -> list[PlayerScore]:
    """Build a sorted scoreboard for all players (descending by score)."""
    scores: list[PlayerScore] = []
    for player in players:
        player_messages = messages_by_player.get(player.id, [])
        scores.append(calculate_player_score(player, player_messages))

    scores.sort(key=lambda s: s.score, reverse=True)
    return scores
