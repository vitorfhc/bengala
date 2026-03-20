"""Tests for fallback word list."""

from __future__ import annotations

from bengala.fallback_words import FALLBACK_WORDS


class TestFallbackWords:
    def test_has_at_least_200_words(self) -> None:
        assert len(FALLBACK_WORDS) >= 200

    def test_all_words_have_4_plus_chars(self) -> None:
        for word in FALLBACK_WORDS:
            assert len(word) >= 4, f"Word '{word}' has fewer than 4 characters"

    def test_no_duplicates(self) -> None:
        assert len(FALLBACK_WORDS) == len(set(FALLBACK_WORDS))
