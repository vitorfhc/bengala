"""Word processing pipeline for forbidden word selection and detection."""

from __future__ import annotations

import random
import re
import unicodedata

from bengala.fallback_words import FALLBACK_WORDS

# URL pattern for removal
_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
# Discord mention pattern
_MENTION_PATTERN = re.compile(r"<[@#!&]\d+>|<:\w+:\d+>")
# Keep only word characters (letters, digits, underscores) and spaces
_NON_WORD_PATTERN = re.compile(r"[^\w\s]", re.UNICODE)

_stop_words_cache: set[str] | None = None


def _get_stop_words() -> set[str]:
    """Load Portuguese stop words from NLTK (cached)."""
    global _stop_words_cache  # noqa: PLW0603
    if _stop_words_cache is None:
        from nltk.corpus import stopwords  # type: ignore[import-untyped]

        _stop_words_cache = set(stopwords.words("portuguese"))
    return _stop_words_cache


def _strip_accents(text: str) -> str:
    """Remove accents from text for normalization."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def tokenize_message(text: str) -> list[str]:
    """Tokenize a message into lowercase words, stripping noise."""
    text = _URL_PATTERN.sub(" ", text)
    text = _MENTION_PATTERN.sub(" ", text)
    text = _NON_WORD_PATTERN.sub(" ", text)
    text = text.lower()
    return text.split()


def filter_tokens(tokens: list[str]) -> set[str]:
    """Filter tokens by removing stop words and short words, then deduplicate."""
    stop_words = _get_stop_words()
    return {
        token
        for token in tokens
        if len(token) >= 4 and token not in stop_words
    }


_MIN_WORD_FREQUENCY = 5


def select_forbidden_word(messages: list[str], min_freq: int = _MIN_WORD_FREQUENCY) -> str:
    """Select a forbidden word from recent messages using the full pipeline.

    Only words that appear at least `min_freq` times are eligible.
    Falls back to a random word from the hardcoded list if no valid words found.
    """
    stop_words = _get_stop_words()
    counts: dict[str, int] = {}
    for msg in messages:
        for token in tokenize_message(msg):
            if len(token) >= 4 and token not in stop_words:
                counts[token] = counts.get(token, 0) + 1

    eligible = [
        word for word, count in counts.items()
        if count >= min_freq and len(set(word)) >= 3
    ]

    if not eligible:
        return random.choice(FALLBACK_WORDS)

    return random.choice(sorted(eligible))


def contains_forbidden_word(text: str, forbidden_word: str) -> bool:
    """Check if text contains the forbidden word as an exact token match."""
    tokens = tokenize_message(text)
    return forbidden_word.lower() in tokens
