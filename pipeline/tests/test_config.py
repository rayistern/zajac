"""Tests for config loader."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pipeline.config import (
    Config,
    LLMConfig,
    _resolve_env_vars,
    load_config,
)


class TestEnvVarResolution:
    def test_resolves_simple_env_var(self, monkeypatch):
        monkeypatch.setenv("MY_KEY", "my-value")
        assert _resolve_env_vars("${MY_KEY}") == "my-value"

    def test_returns_empty_for_missing_env_var(self, monkeypatch):
        monkeypatch.delenv("MISSING_KEY", raising=False)
        assert _resolve_env_vars("${MISSING_KEY}") == ""

    def test_passes_through_non_env_strings(self):
        assert _resolve_env_vars("plain string") == "plain string"
        assert _resolve_env_vars("not-env ${partial") == "not-env ${partial"

    def test_recurses_into_dict(self, monkeypatch):
        monkeypatch.setenv("NESTED_KEY", "nested-val")
        result = _resolve_env_vars({"a": "${NESTED_KEY}", "b": "static"})
        assert result == {"a": "nested-val", "b": "static"}

    def test_recurses_into_list(self, monkeypatch):
        monkeypatch.setenv("LIST_KEY", "list-val")
        result = _resolve_env_vars(["${LIST_KEY}", "plain"])
        assert result == ["list-val", "plain"]

    def test_handles_nested_structures(self, monkeypatch):
        monkeypatch.setenv("DEEP", "value")
        result = _resolve_env_vars({"a": [{"b": "${DEEP}"}]})
        assert result == {"a": [{"b": "value"}]}

    def test_preserves_non_string_values(self):
        assert _resolve_env_vars(42) == 42
        assert _resolve_env_vars(True) is True
        assert _resolve_env_vars(None) is None


class TestConfigDefaults:
    def test_creates_config_with_defaults(self):
        c = Config()
        assert c.pipeline.log_level == "INFO"
        assert c.pipeline.log_format == "json"
        assert c.transcription.primary_provider == "sofer_ai"
        assert c.sefaria.base_url == "https://www.sefaria.org/api"
        assert c.sefaria.cache_ttl_days == 30
        assert c.approval.min_approval_percentage == 70
        assert c.approval.min_total_votes == 3
        assert c.whatsapp.rate_limit_per_second == 20

    def test_llm_config_defaults(self):
        llm = LLMConfig()
        assert llm.provider == "anthropic"
        assert llm.model == "claude-sonnet-4-20250514"

    def test_styles_config_has_five_styles(self):
        c = Config()
        assert len(c.image_generation.styles.enabled) == 5
        assert "photorealistic" in c.image_generation.styles.enabled
        assert "watercolor" in c.image_generation.styles.enabled


class TestLoadConfig:
    def test_returns_defaults_for_missing_file(self, tmp_path):
        config = load_config(tmp_path / "nonexistent.yaml")
        assert config.pipeline.log_level == "INFO"

    def test_loads_from_yaml(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_VOTING_CHAT_ID", raising=False)

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
pipeline:
  log_level: DEBUG
  log_format: pretty
approval:
  min_approval_percentage: 80
  min_total_votes: 5
"""
        )
        config = load_config(config_file)
        assert config.pipeline.log_level == "DEBUG"
        assert config.pipeline.log_format == "pretty"
        assert config.approval.min_approval_percentage == 80
        assert config.approval.min_total_votes == 5

    def test_resolves_env_vars_in_yaml(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MY_DB_URL", "postgresql://test/db")
        config_file = tmp_path / "config.yaml"
        config_file.write_text("database_url: ${MY_DB_URL}")
        config = load_config(config_file)
        assert config.database_url == "postgresql://test/db"

    def test_pulls_database_url_from_env_when_not_in_yaml(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://env/db")
        config_file = tmp_path / "config.yaml"
        config_file.write_text("pipeline:\n  log_level: INFO\n")
        config = load_config(config_file)
        assert config.database_url == "postgresql://env/db"

    def test_pulls_telegram_secrets_from_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-123")
        monkeypatch.setenv("TELEGRAM_VOTING_CHAT_ID", "chat-456")
        config_file = tmp_path / "config.yaml"
        config_file.write_text("pipeline:\n  log_level: INFO\n")
        config = load_config(config_file)
        assert config.telegram.bot_token == "bot-123"
        assert config.telegram.voting_group_chat_id == "chat-456"

    def test_env_override_does_not_clobber_yaml_values(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "from-env")
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
telegram:
  bot_token: from-yaml
"""
        )
        config = load_config(config_file)
        # YAML value should win when present
        assert config.telegram.bot_token == "from-yaml"
