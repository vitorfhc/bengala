"""Tests for scoring logic."""

from __future__ import annotations

from datetime import datetime, timezone

from bengala.models import MessageData, PlayerData, PlayerScore
from bengala.scoring import build_scoreboard, calculate_player_score


def _make_msg(
    player_id: int, content: str, minute: int = 0
) -> MessageData:
    return MessageData(
        id=0,
        round_id=1,
        player_id=player_id,
        content=content,
        sent_at=datetime(2025, 1, 1, 12, minute, tzinfo=timezone.utc),
    )


class TestCalculatePlayerScore:
    def test_basic_scoring(self) -> None:
        player = PlayerData(id=1, round_id=1, user_id=100, username="alice")
        messages = [
            _make_msg(1, "O abacaxi estava maduro delicioso"),
        ]
        score = calculate_player_score(player, messages)
        assert score.score > 0
        assert score.muted is False

    def test_muted_player_only_pre_mute_messages(self) -> None:
        mute_time = datetime(2025, 1, 1, 12, 5, tzinfo=timezone.utc)
        player = PlayerData(
            id=1, round_id=1, user_id=100, username="bob", muted_at=mute_time
        )
        messages = [
            _make_msg(1, "abacaxi banana", minute=1),  # before mute
            _make_msg(1, "laranja morango", minute=10),  # after mute
        ]
        score = calculate_player_score(player, messages)
        assert score.muted is True
        # Should only count words from the first message
        assert score.score == 2  # abacaxi, banana

    def test_zero_messages(self) -> None:
        player = PlayerData(id=1, round_id=1, user_id=100, username="carlos")
        score = calculate_player_score(player, [])
        assert score.score == 0


class TestBuildScoreboard:
    def test_sorted_descending(self) -> None:
        p1 = PlayerData(id=1, round_id=1, user_id=100, username="alice")
        p2 = PlayerData(id=2, round_id=1, user_id=101, username="bob")
        messages = {
            1: [_make_msg(1, "abacaxi banana laranja morango")],
            2: [_make_msg(2, "cachorro")],
        }
        scores = build_scoreboard([p1, p2], messages)
        assert scores[0].username == "alice"
        assert scores[1].username == "bob"
        assert scores[0].score > scores[1].score
