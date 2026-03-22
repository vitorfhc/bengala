"""Tests for the word processing pipeline."""

from __future__ import annotations

from unittest.mock import patch

from bengala.word_pipeline import (
    contains_forbidden_word,
    filter_tokens,
    get_plural_variants,
    select_forbidden_word,
    tokenize_message,
)


class TestTokenizeMessage:
    def test_basic_tokenization(self) -> None:
        tokens = tokenize_message("Olá mundo como vai")
        assert tokens == ["olá", "mundo", "como", "vai"]

    def test_removes_punctuation(self) -> None:
        tokens = tokenize_message("Olá, mundo! Como vai?")
        assert "olá" in tokens
        assert "mundo" in tokens

    def test_removes_urls(self) -> None:
        tokens = tokenize_message("Veja https://example.com aqui")
        assert "https" not in " ".join(tokens)
        assert "example" not in " ".join(tokens)
        assert "veja" in tokens
        assert "aqui" in tokens

    def test_removes_mentions(self) -> None:
        tokens = tokenize_message("Oi <@123456> tudo bem")
        assert "<@123456>" not in tokens
        assert "oi" in tokens
        assert "tudo" in tokens

    def test_lowercase(self) -> None:
        tokens = tokenize_message("GATO Cachorro")
        assert tokens == ["gato", "cachorro"]

    def test_empty_message(self) -> None:
        tokens = tokenize_message("")
        assert tokens == []

    def test_emojis_stripped(self) -> None:
        tokens = tokenize_message("legal 🎮 demais")
        assert "legal" in tokens
        assert "demais" in tokens


class TestFilterTokens:
    def test_removes_short_words(self) -> None:
        result = filter_tokens(["oi", "sim", "abacaxi", "casa"])
        assert "oi" not in result
        assert "sim" not in result
        assert "abacaxi" in result
        assert "casa" in result

    def test_deduplicates(self) -> None:
        result = filter_tokens(["gato", "gato", "gato", "cachorro"])
        assert result == {"gato", "cachorro"}

    def test_removes_stop_words(self) -> None:
        # "para", "como", "mais" are Portuguese stop words
        result = filter_tokens(["para", "como", "mais", "abacaxi"])
        assert "abacaxi" in result
        # Stop words with < 4 chars would be filtered anyway,
        # but "para" and "como" and "mais" are all 4 chars and are stop words
        assert "para" not in result
        assert "como" not in result
        assert "mais" not in result


class TestGetPluralVariants:
    def test_always_contains_original(self) -> None:
        assert "gato" in get_plural_variants("gato")
        assert "flores" in get_plural_variants("flores")

    # Rule 5: default -s
    def test_singular_to_plural_s(self) -> None:
        assert "gatos" in get_plural_variants("gato")
        assert "coisas" in get_plural_variants("coisa")

    def test_plural_s_to_singular(self) -> None:
        assert "gato" in get_plural_variants("gatos")
        assert "coisa" in get_plural_variants("coisas")

    # Rule 1: -ão ↔ -ões / -ães / -ãos
    def test_ao_to_plurals(self) -> None:
        variants = get_plural_variants("coração")
        assert "corações" in variants
        assert "coraçães" in variants
        assert "coraçãos" in variants

    def test_oes_to_singular(self) -> None:
        variants = get_plural_variants("corações")
        assert "coração" in variants

    def test_aes_to_singular(self) -> None:
        variants = get_plural_variants("pães")
        assert "pão" in variants

    def test_aos_to_singular(self) -> None:
        variants = get_plural_variants("irmãos")
        assert "irmão" in variants

    # Rule 2: -m ↔ -ns
    def test_m_to_ns(self) -> None:
        assert "homens" in get_plural_variants("homem")

    def test_ns_to_m(self) -> None:
        assert "homem" in get_plural_variants("homens")

    # Rule 3: -l ↔ -is
    def test_l_to_is(self) -> None:
        assert "animais" in get_plural_variants("animal")

    def test_is_to_l(self) -> None:
        assert "animal" in get_plural_variants("animais")

    def test_el_to_eis(self) -> None:
        assert "papéis" in get_plural_variants("papel")

    def test_eis_to_el(self) -> None:
        assert "papel" in get_plural_variants("papéis")

    # Rule 4: -r / -z + -es
    def test_r_to_res(self) -> None:
        assert "flores" in get_plural_variants("flor")

    def test_res_to_r(self) -> None:
        assert "flor" in get_plural_variants("flores")

    def test_z_to_zes(self) -> None:
        assert "vezes" in get_plural_variants("vez")

    def test_zes_to_z(self) -> None:
        assert "vez" in get_plural_variants("vezes")


class TestSelectForbiddenWord:
    def test_selects_word_with_enough_frequency(self) -> None:
        # "abacaxi" appears 5 times, should be eligible
        messages = ["abacaxi"] * 5 + ["delicioso"]
        word = select_forbidden_word(messages)
        assert word == "abacaxi"

    def test_fallback_when_below_min_frequency(self) -> None:
        # "abacaxi" appears only once — below threshold, triggers fallback
        messages = ["O abacaxi estava maduro e delicioso"]
        word = select_forbidden_word(messages)
        from bengala.fallback_words import FALLBACK_WORDS
        assert word in FALLBACK_WORDS

    def test_custom_min_freq(self) -> None:
        messages = ["abacaxi delicioso", "abacaxi maduro"]
        # With min_freq=2, "abacaxi" qualifies
        word = select_forbidden_word(messages, min_freq=2)
        assert word == "abacaxi"

    def test_fallback_on_empty(self) -> None:
        word = select_forbidden_word([])
        assert isinstance(word, str)
        assert len(word) >= 4

    def test_fallback_on_only_stopwords(self) -> None:
        messages = ["é de da do em no na"]
        word = select_forbidden_word(messages)
        assert isinstance(word, str)
        assert len(word) >= 4

    def test_only_frequent_words_eligible(self) -> None:
        # "gato" x5, "cachorro" x2 — only "gato" qualifies
        messages = ["gato"] * 5 + ["cachorro"] * 2
        word = select_forbidden_word(messages)
        assert word == "gato"

    def test_rejects_words_with_fewer_than_3_distinct_letters(self) -> None:
        # "abab" has only 2 distinct letters — should be rejected
        messages = ["abab"] * 10 + ["gato"] * 5
        word = select_forbidden_word(messages, min_freq=5)
        assert word == "gato"

    def test_fallback_when_all_words_have_few_distinct_letters(self) -> None:
        messages = ["aaaa"] * 10 + ["abab"] * 10
        word = select_forbidden_word(messages, min_freq=5)
        from bengala.fallback_words import FALLBACK_WORDS
        assert word in FALLBACK_WORDS

    def test_groups_singular_and_plural_for_frequency(self) -> None:
        # "gato" x3 + "gatos" x2 = 5 total — should be eligible
        messages = ["gato"] * 3 + ["gatos"] * 2
        word = select_forbidden_word(messages, min_freq=5)
        assert word in ("gato", "gatos")

    def test_groups_ao_oes_for_frequency(self) -> None:
        messages = ["dragão"] * 3 + ["dragões"] * 3
        word = select_forbidden_word(messages, min_freq=5)
        assert word in ("dragão", "dragões")


class TestContainsForbiddenWord:
    def test_exact_match(self) -> None:
        assert contains_forbidden_word("eu gosto de gato", "gato") is True

    def test_case_insensitive(self) -> None:
        assert contains_forbidden_word("Eu gosto de GATO", "gato") is True

    def test_no_substring_match(self) -> None:
        assert contains_forbidden_word("eu vi um gatoca", "gato") is False

    def test_no_prefix_match(self) -> None:
        assert contains_forbidden_word("eu vi um mingato", "gato") is False

    def test_not_present(self) -> None:
        assert contains_forbidden_word("eu gosto de cachorro", "gato") is False

    def test_with_punctuation(self) -> None:
        assert contains_forbidden_word("gato, cachorro!", "gato") is True

    def test_plural_s_matches(self) -> None:
        assert contains_forbidden_word("eu vi dois gatos", "gato") is True

    def test_singular_matches_plural_word(self) -> None:
        assert contains_forbidden_word("eu vi um gato", "gatos") is True

    def test_plural_oes_matches(self) -> None:
        assert contains_forbidden_word("dois corações", "coração") is True

    def test_plural_ns_matches(self) -> None:
        assert contains_forbidden_word("os homens saíram", "homem") is True

    def test_plural_is_matches(self) -> None:
        assert contains_forbidden_word("os animais fugiram", "animal") is True

    def test_unrelated_word_no_false_positive(self) -> None:
        assert contains_forbidden_word("eu vi a casa", "casar") is False

    def test_substring_still_no_match(self) -> None:
        assert contains_forbidden_word("os gatinhos são fofos", "gato") is False
