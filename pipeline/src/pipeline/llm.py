"""Unified LLM client with a provider cascade.

Resolution order (first present key wins):
  1. AI_GATEWAY_API_KEY  — Vercel AI Gateway (preferred; same key as api/)
  2. OPENROUTER_API_KEY  — OpenRouter (legacy; kept working for standalone
                           runs that still point at it)
  3. ANTHROPIC_API_KEY   — direct Anthropic (last-resort fallback)

Why cascade? The gateway is where we want long-term traffic — it's where
the api/ chatbot lives, and it gives us a single billing/observability
surface for *every* LLM call in the product. But the pipeline can run
standalone (dev loops, one-off backfills), and we don't want to force
anyone to stand up the gateway for that. So we keep OpenRouter + direct
Anthropic as working fallbacks and let the environment decide.

Gateway + OpenRouter both speak the OpenAI chat-completions shape, so we
route them through the same ``OpenAI`` client with a different base_url.
Model ids use the ``provider/model`` format gateway expects; we translate
``claude-sonnet-4-YYYYMMDD`` → ``anthropic/claude-sonnet-4`` in both cases.
"""

from __future__ import annotations

import os

import structlog

logger = structlog.get_logger()


class LLMClient:
    """Provider-agnostic LLM client with a `complete(prompt, max_tokens)` method."""

    # Vercel AI Gateway's OpenAI-compatible endpoint. Hard-coded because
    # it's part of our infra contract, not a runtime choice.
    GATEWAY_BASE_URL = "https://ai-gateway.vercel.sh/v1"
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self._anthropic = None
        self._openai = None

        gateway_key = os.environ.get("AI_GATEWAY_API_KEY")
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")

        if gateway_key:
            # Preferred path — same gateway the api/ chatbot uses.
            from openai import OpenAI
            self._openai = OpenAI(
                base_url=self.GATEWAY_BASE_URL,
                api_key=gateway_key,
            )
            self.provider = "gateway"
            self._model_id = self._to_gateway_model(model)
            logger.info("llm.using_gateway", model=self._model_id)
        elif openrouter_key:
            from openai import OpenAI
            self._openai = OpenAI(
                base_url=self.OPENROUTER_BASE_URL,
                api_key=openrouter_key,
            )
            # OpenRouter uses the same provider/model shape the gateway does,
            # so the translation helper is shared.
            self.provider = "openrouter"
            self._model_id = self._to_gateway_model(model)
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

    def _to_gateway_model(self, anthropic_model: str) -> str:
        """Convert Anthropic model names to gateway/OpenRouter format.

        Anthropic direct uses dated slugs:  ``claude-sonnet-4-20250514``
        Gateway + OpenRouter use a provider prefix with the date stripped:
                                           ``anthropic/claude-sonnet-4``

        Non-Claude models (``gpt-4o``, ``gemini-…``) are passed through
        untouched — the caller is trusted to have already supplied a valid
        provider/model string for those.
        """
        if anthropic_model.startswith("claude-"):
            base = anthropic_model
            parts = base.split("-")
            # Rejoin everything before the date (YYYYMMDD at end)
            if parts and parts[-1].isdigit() and len(parts[-1]) == 8:
                base = "-".join(parts[:-1])
            return f"anthropic/{base}"
        return anthropic_model
