"""Tests for config.settings."""

import pytest

from config.settings import Settings, _env_bool, _env_int
from core.exceptions import ConfigurationError


class TestEnvParsers:
    def test_env_int_falls_back_on_garbage(self, monkeypatch):
        monkeypatch.setenv("SOME_INT", "not-a-number")
        assert _env_int("SOME_INT", 42) == 42

    def test_env_int_parses_valid(self, monkeypatch):
        monkeypatch.setenv("SOME_INT", "7")
        assert _env_int("SOME_INT", 42) == 7

    def test_env_int_missing_uses_default(self, monkeypatch):
        monkeypatch.delenv("SOME_INT", raising=False)
        assert _env_int("SOME_INT", 42) == 42

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "Yes", "on"])
    def test_env_bool_truthy(self, monkeypatch, value):
        monkeypatch.setenv("SOME_FLAG", value)
        assert _env_bool("SOME_FLAG") is True

    @pytest.mark.parametrize("value", ["0", "false", "nope", ""])
    def test_env_bool_falsy(self, monkeypatch, value):
        monkeypatch.setenv("SOME_FLAG", value)
        assert _env_bool("SOME_FLAG") is False


class TestValidate:
    def test_missing_secret_key_raises_outside_debug(self, monkeypatch):
        monkeypatch.setattr(Settings, "SECRET_KEY", "")
        monkeypatch.setattr(Settings, "DEBUG", False)
        with pytest.raises(ConfigurationError, match="SECRET_KEY"):
            Settings.validate()

    def test_debug_generates_ephemeral_secret(self, monkeypatch):
        monkeypatch.setattr(Settings, "SECRET_KEY", "")
        monkeypatch.setattr(Settings, "DEBUG", True)
        Settings.validate()
        assert len(Settings.SECRET_KEY) == 64  # token_hex(32)

    def test_explicit_secret_passes(self, monkeypatch):
        monkeypatch.setattr(Settings, "SECRET_KEY", "a-real-secret")
        monkeypatch.setattr(Settings, "DEBUG", False)
        Settings.validate()

    def test_negative_window_rejected(self, monkeypatch):
        monkeypatch.setattr(Settings, "SECRET_KEY", "x")
        monkeypatch.setattr(Settings, "VALIDATION_WINDOW_MINUTES", -1)
        with pytest.raises(ConfigurationError):
            Settings.validate()


class TestToDict:
    def test_secrets_excluded(self):
        d = Settings.to_dict()
        assert "SECRET_KEY" not in d
        assert "VAULT_TOKEN" not in d
        assert "PORT" in d
