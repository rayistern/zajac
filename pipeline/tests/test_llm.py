"""Tests for the LLM client routing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipeline.llm import LLMClient


class TestModelNameTranslation:
    # These tests exercise the shared translation helper via OpenRouter's
    # branch of the cascade — the same helper is reused for gateway, so
    # a bug in one fixes both.
    def test_strips_date_suffix_for_openrouter(self, monkeypatch):
        monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        with patch("openai.OpenAI"):
            client = LLMClient("claude-sonnet-4-20250514")
        assert client._model_id == "anthropic/claude-sonnet-4"

    def test_keeps_non_date_suffix(self, monkeypatch):
        monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        with patch("openai.OpenAI"):
            client = LLMClient("claude-haiku-4-5")
        assert client._model_id == "anthropic/claude-haiku-4-5"

    def test_non_claude_models_passthrough(self, monkeypatch):
        monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        with patch("openai.OpenAI"):
            client = LLMClient("gpt-4o")
        assert client._model_id == "gpt-4o"


class TestProviderSelection:
    def test_gateway_wins_when_all_keys_set(self, monkeypatch):
        # Cascade priority: gateway > openrouter > anthropic. This test
        # is the regression signal for the priority order — if someone
        # inadvertently swaps branches, this fails loudly.
        monkeypatch.setenv("AI_GATEWAY_API_KEY", "gw-key")
        monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-key")
        with patch("openai.OpenAI") as mock_openai:
            client = LLMClient("claude-sonnet-4")
        assert client.provider == "gateway"
        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args.kwargs
        assert call_kwargs["base_url"] == LLMClient.GATEWAY_BASE_URL
        assert call_kwargs["api_key"] == "gw-key"

    def test_uses_openrouter_when_only_or_key_set(self, monkeypatch):
        monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
        with patch("openai.OpenAI") as mock_openai:
            client = LLMClient("claude-sonnet-4")
        assert client.provider == "openrouter"
        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args.kwargs
        assert call_kwargs["base_url"] == LLMClient.OPENROUTER_BASE_URL
        assert call_kwargs["api_key"] == "or-key"

    def test_falls_back_to_anthropic_direct(self, monkeypatch):
        monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-key")
        with patch("anthropic.Anthropic") as mock_anthropic:
            client = LLMClient("claude-sonnet-4")
        assert client.provider == "anthropic"
        mock_anthropic.assert_called_once()

    def test_gateway_translates_claude_model_id(self, monkeypatch):
        # Gateway expects the same provider/model shape as OpenRouter, so
        # _to_gateway_model must be applied on this branch too.
        monkeypatch.setenv("AI_GATEWAY_API_KEY", "gw-key")
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        with patch("openai.OpenAI"):
            client = LLMClient("claude-sonnet-4-20250514")
        assert client._model_id == "anthropic/claude-sonnet-4"


class TestComplete:
    def test_openrouter_complete_returns_message_content(self, monkeypatch):
        monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
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
        monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
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
        monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
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

    def test_gateway_complete_uses_translated_model_id(self, monkeypatch):
        # Gateway branch shares the OpenAI-shaped client but hits a
        # different base_url; asserting the call args covers both.
        monkeypatch.setenv("AI_GATEWAY_API_KEY", "gw-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="gateway response"))]

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            client = LLMClient("claude-sonnet-4-20250514")
            result = client.complete("hi", max_tokens=200)

        assert result == "gateway response"
        assert client.provider == "gateway"
        mock_client.chat.completions.create.assert_called_once_with(
            model="anthropic/claude-sonnet-4",
            max_tokens=200,
            messages=[{"role": "user", "content": "hi"}],
        )

    def test_default_max_tokens(self, monkeypatch):
        monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
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
