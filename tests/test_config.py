"""Tests for configuration loading."""

from __future__ import annotations

import pytest

from bengala.config import load_config


class TestLoadConfig:
    def test_loads_valid_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DISCORD_TOKEN", "test-token")
        monkeypatch.setenv("WATCHED_CHANNEL_ID", "123")
        monkeypatch.setenv("ADMIN_ROLE_ID", "789")

        config = load_config()

        assert config.discord_token == "test-token"
        assert config.watched_channel_id == 123
        assert config.admin_role_id == 789

    def test_raises_on_missing_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DISCORD_TOKEN", raising=False)
        monkeypatch.setenv("WATCHED_CHANNEL_ID", "123")
        monkeypatch.setenv("ADMIN_ROLE_ID", "789")

        with pytest.raises(ValueError, match="DISCORD_TOKEN"):
            load_config()

    def test_raises_on_missing_multiple(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DISCORD_TOKEN", raising=False)
        monkeypatch.delenv("WATCHED_CHANNEL_ID", raising=False)
        monkeypatch.delenv("ADMIN_ROLE_ID", raising=False)

        with pytest.raises(ValueError):
            load_config()

    def test_raises_on_non_numeric_channel_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DISCORD_TOKEN", "test-token")
        monkeypatch.setenv("WATCHED_CHANNEL_ID", "not-a-number")
        monkeypatch.setenv("ADMIN_ROLE_ID", "789")

        with pytest.raises(ValueError, match="inteiros"):
            load_config()
