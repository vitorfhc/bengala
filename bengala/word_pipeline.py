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


def get_plural_variants(word: str) -> frozenset[str]:
    """Return a word and its plausible Portuguese singular/plural variants."""
    variants = {word}

    # Rule 1: -ão ↔ -ões / -ães / -ãos
    if word.endswith("ão"):
        stem = word[:-2]
        variants.update([stem + "ões", stem + "ães", stem + "ãos"])
    elif word.endswith("ões"):
        stem = word[:-3]
        variants.update([stem + "ão", stem + "ães", stem + "ãos"])
    elif word.endswith("ães"):
        stem = word[:-3]
        variants.update([stem + "ão", stem + "ões", stem + "ãos"])
    elif word.endswith("ãos"):
        stem = word[:-3]
        variants.update([stem + "ão", stem + "ões", stem + "ães"])

    # Rule 2: -m ↔ -ns
    elif word.endswith("m"):
        variants.add(word[:-1] + "ns")
    elif word.endswith("ns"):
        variants.add(word[:-2] + "m")

    # Rule 3: -l ↔ -is  (special: -el ↔ -éis)
    elif word.endswith("el"):
        variants.add(word[:-2] + "éis")
    elif word.endswith("éis"):
        variants.add(word[:-3] + "el")
    elif word.endswith("l"):
        variants.add(word[:-1] + "is")
    elif word.endswith("is") and len(word) >= 3:
        variants.add(word[:-2] + "l")

    # Rule 4: -r / -z / -s + -es
    elif word.endswith(("r", "z")):
        variants.add(word + "es")
    elif word.endswith("res") and len(word) >= 4:
        variants.add(word[:-2])
    elif word.endswith("zes") and len(word) >= 4:
        variants.add(word[:-2])
    elif word.endswith("ses") and len(word) >= 4:
        variants.add(word[:-2])

    # Rule 5: default -s
    elif word.endswith("s"):
        variants.add(word[:-1])
    else:
        variants.add(word + "s")

    return frozenset(variants)


def _group_variants(counts: dict[str, int]) -> dict[str, int]:
    """Group plural variants together, summing their counts.

    Returns a dict mapping the most frequent form to the total count.
    """
    grouped: dict[str, int] = {}
    canonical: dict[str, str] = {}

    for word in sorted(counts, key=counts.__getitem__, reverse=True):
        variants = get_plural_variants(word)
        leader = None
        for v in variants:
            if v in canonical:
                leader = canonical[v]
                break

        if leader is None:
            leader = word

        canonical[word] = leader
        for v in variants:
            if v not in canonical:
                canonical[v] = leader

        grouped[leader] = grouped.get(leader, 0) + counts[word]

    return grouped


_MIN_WORD_FREQUENCY = 5


def select_forbidden_word(messages: list[str], min_freq: int = _MIN_WORD_FREQUENCY) -> str:
    """Select a forbidden word from recent messages using the full pipeline.

    Only words that appear at least `min_freq` times are eligible.
    Plural variants (e.g. gato/gatos) are grouped together for counting.
    Falls back to a random word from the hardcoded list if no valid words found.
    """
    stop_words = _get_stop_words()
    counts: dict[str, int] = {}
    for msg in messages:
        for token in tokenize_message(msg):
            if len(token) >= 4 and token not in stop_words:
                counts[token] = counts.get(token, 0) + 1

    grouped = _group_variants(counts)

    eligible = [
        word for word, count in grouped.items()
        if count >= min_freq and len(set(word)) >= 3
    ]

    if not eligible:
        return random.choice(FALLBACK_WORDS)

    return random.choice(sorted(eligible))


def contains_forbidden_word(text: str, forbidden_word: str) -> bool:
    """Check if text contains the forbidden word or its plural variants."""
    tokens = tokenize_message(text)
    variants = get_plural_variants(forbidden_word.lower())
    return bool(variants & set(tokens))
