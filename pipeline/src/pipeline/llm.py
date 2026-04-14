"""Unified LLM client that routes through OpenRouter or direct Anthropic.

If OPENROUTER_API_KEY is set, uses OpenRouter (via OpenAI SDK) — a single key
gives access to Claude, GPT-4, Gemini, etc. Otherwise falls back to direct
Anthropic API with ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import os

import structlog

logger = structlog.get_logger()


class LLMClient:
    """Provider-agnostic LLM client with a `complete(prompt, max_tokens)` method."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self._anthropic = None
        self._openai = None

        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if openrouter_key:
            from openai import OpenAI
            self._openai = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
            )
            # OpenRouter model names: "anthropic/claude-sonnet-4"
            self.provider = "openrouter"
            self._model_id = self._to_openrouter_model(model)
            logger.info("llm.using_openrouter", model=self._model_id)
        else:
            import anthropic
            self._anthropic = anthropic.Anthropic()
            self.provider = "anthropic"
            self._model_id = model
            logger.info("llm.using_anthropic_direct", model=self._model_id)

    def complete(self, prompt: str, max_tokens: int = 1024) -> str:
        """Send a single user message, return the completion text."""
        if self._openai is not None:
            resp = self._openai.chat.completions.create(
                model=self._model_id,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content or ""

        resp = self._anthropic.messages.create(
            model=self._model_id,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text

    def _to_openrouter_model(self, anthropic_model: str) -> str:
        """Convert Anthropic model names to OpenRouter format."""
        # Anthropic: "claude-sonnet-4-20250514" → OpenRouter: "anthropic/claude-sonnet-4"
        if anthropic_model.startswith("claude-"):
            # Strip date suffix if present
            base = anthropic_model
            parts = base.split("-")
            # Rejoin everything before the date (YYYYMMDD at end)
            if parts and parts[-1].isdigit() and len(parts[-1]) == 8:
                base = "-".join(parts[:-1])
            return f"anthropic/{base}"
        return anthropic_model
