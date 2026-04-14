"""Tests for the LLM client routing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipeline.llm import LLMClient


class TestModelNameTranslation:
    def test_strips_date_suffix_for_openrouter(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        with patch("openai.OpenAI"):
            client = LLMClient("claude-sonnet-4-20250514")
        assert client._model_id == "anthropic/claude-sonnet-4"

    def test_keeps_non_date_suffix(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        with patch("openai.OpenAI"):
            client = LLMClient("claude-haiku-4-5")
        assert client._model_id == "anthropic/claude-haiku-4-5"

    def test_non_claude_models_passthrough(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        with patch("openai.OpenAI"):
            client = LLMClient("gpt-4o")
        assert client._model_id == "gpt-4o"


class TestProviderSelection:
    def test_uses_openrouter_when_key_set(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
        with patch("openai.OpenAI") as mock_openai:
            client = LLMClient("claude-sonnet-4")
        assert client.provider == "openrouter"
        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args.kwargs
        assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"
        assert call_kwargs["api_key"] == "or-key"

    def test_falls_back_to_anthropic_direct(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-key")
        with patch("anthropic.Anthropic") as mock_anthropic:
            client = LLMClient("claude-sonnet-4")
        assert client.provider == "anthropic"
        mock_anthropic.assert_called_once()


class TestComplete:
    def test_openrouter_complete_returns_message_content(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="response text"))]

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            client = LLMClient("claude-haiku-4-5")
            result = client.complete("hello", max_tokens=100)

        assert result == "response text"
        mock_client.chat.completions.create.assert_called_once_with(
            model="anthropic/claude-haiku-4-5",
            max_tokens=100,
            messages=[{"role": "user", "content": "hello"}],
        )

    def test_openrouter_handles_empty_content(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            client = LLMClient("claude-haiku-4-5")
            result = client.complete("hello")

        assert result == ""

    def test_anthropic_complete_returns_text(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="anthropic response")]

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            client = LLMClient("claude-sonnet-4-20250514")
            result = client.complete("test prompt", max_tokens=500)

        assert result == "anthropic response"
        mock_client.messages.create.assert_called_once_with(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": "test prompt"}],
        )

    def test_default_max_tokens(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            client = LLMClient("claude-haiku-4-5")
            client.complete("hello")  # no explicit max_tokens

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 1024
