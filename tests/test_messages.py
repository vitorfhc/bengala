"""Tests for message formatting."""

from __future__ import annotations

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
from bengala.models import PlayerScore


class TestFormatFinalScoreboard:
    def test_with_players(self) -> None:
        scores = [
            PlayerScore(user_id=1, username="alice", score=42),
            PlayerScore(user_id=2, username="bob", score=31),
            PlayerScore(user_id=3, username="diana", score=5, muted=True),
        ]
        result = format_final_scoreboard("abacaxi", scores)
        assert "abacaxi" in result
        assert "@alice" in result
        assert "42 pontos" in result
        assert "bengalado" in result
        assert "🤡" in result

    def test_no_players(self) -> None:
        result = format_final_scoreboard("abacaxi", [])
        assert "abacaxi" in result
        assert "Nenhum jogador" in result

    def test_single_point(self) -> None:
        scores = [PlayerScore(user_id=1, username="alice", score=1)]
        result = format_final_scoreboard("teste", scores)
        assert "1 ponto" in result
        assert "1 pontos" not in result


class TestFormatPartialScoreboard:
    def test_with_players(self) -> None:
        scores = [
            PlayerScore(user_id=1, username="alice", score=38),
            PlayerScore(user_id=2, username="bob", score=5, muted=True),
        ]
        result = format_partial_scoreboard(scores)
        assert "@alice" in result
        assert "@bob" in result
        # Should NOT reveal punishment status
        assert "bengalado" not in result
        assert "🤡" not in result

    def test_no_players(self) -> None:
        result = format_partial_scoreboard([])
        assert "Nenhum jogador" in result


class TestOtherMessages:
    def test_rules(self) -> None:
        result = format_rules()
        assert "Bengala" in result
        assert "proibida" in result

    def test_mute_notice(self) -> None:
        result = format_mute_notice()
        assert "bengalado" in result

    def test_already_muted(self) -> None:
        result = format_already_muted_notice()
        assert "bengalado" in result

    def test_secret_word(self) -> None:
        result = format_secret_word("abacaxi")
        assert "abacaxi" in result

    def test_no_active_round(self) -> None:
        result = format_no_active_round()
        assert len(result) > 0

    def test_no_permission(self) -> None:
        result = format_no_permission()
        assert "permissão" in result

    def test_restart_confirmation(self) -> None:
        result = format_restart_confirmation()
        assert "reiniciado" in result
