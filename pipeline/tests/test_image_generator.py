"""Tests for image generator — prompt building, style selection, routing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.config import (
    ImageGenerationConfig,
    OpenRouterImageConfig,
    ReplicateConfig,
    StylesConfig,
)
from pipeline.image_generator import ImageGenerator


@pytest.fixture
def config():
    return ImageGenerationConfig(
        provider="openrouter",
        openrouter=OpenRouterImageConfig(model="google/gemini-2.5-flash-image"),
        replicate=ReplicateConfig(model="black-forest-labs/flux-1.1-pro"),
        styles=StylesConfig(
            enabled=["photorealistic", "watercolor", "cartoon"],
            rotation="random_per_image",
            default="photorealistic",
        ),
    )


@pytest.fixture
def generator(config):
    session = MagicMock()
    return ImageGenerator(config, session)


class TestPromptBuilding:
    def test_combines_base_style_context_and_focus(self, generator):
        generator.style_prompts = {
            "base": "BASE_PROMPT",
            "styles": {"watercolor": "WATERCOLOR_STYLE"},
        }
        result = generator._build_prompt(
            context="A Torah scroll scene",
            prompt_focus="Open scroll on table",
            style_name="watercolor",
        )
        assert "BASE_PROMPT" in result
        assert "WATERCOLOR_STYLE" in result
        assert "A Torah scroll scene" in result
        assert "Open scroll on table" in result

    def test_missing_style_returns_empty_style_section(self, generator):
        generator.style_prompts = {"base": "BASE", "styles": {}}
        result = generator._build_prompt("ctx", "focus", "unknown_style")
        assert "BASE" in result
        assert "ctx" in result
        assert "focus" in result

    def test_missing_prompts_file_returns_empty_dict(self, generator):
        # When no prompts file exists, style_prompts is {}
        generator.style_prompts = {}
        result = generator._build_prompt("ctx", "focus", "watercolor")
        # Should still have the user-supplied content
        assert "ctx" in result
        assert "focus" in result


class TestStyleSelection:
    def test_random_rotation_picks_from_enabled(self, generator):
        styles = set()
        for _ in range(50):
            styles.add(generator._pick_style())
        # With random_per_image + 50 draws, should hit all 3
        assert styles.issubset({"photorealistic", "watercolor", "cartoon"})
        assert len(styles) >= 2  # at least 2 out of 3 in 50 draws (very safe)

    def test_non_random_rotation_returns_default(self, config):
        config.styles.rotation = "fixed"
        gen = ImageGenerator(config, MagicMock())
        for _ in range(10):
            assert gen._pick_style() == "photorealistic"


class TestActiveModel:
    def test_openrouter_provider_returns_openrouter_model(self, generator):
        assert generator._active_model() == "google/gemini-2.5-flash-image"

    def test_replicate_provider_returns_replicate_model(self, config):
        config.provider = "replicate"
        gen = ImageGenerator(config, MagicMock())
        assert gen._active_model() == "black-forest-labs/flux-1.1-pro"


class TestOpenRouterGeneration:
    def test_raises_when_key_missing(self, generator, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
            generator._generate_via_openrouter("test prompt")

    def test_extracts_image_url_from_response(self, generator, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_msg = MagicMock()
        mock_msg.content = None
        mock_msg.images = [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,ABC"}}
        ]
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=mock_msg)]

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_resp
            mock_openai_cls.return_value = mock_client

            result = generator._generate_via_openrouter("prompt")

        assert result == "data:image/png;base64,ABC"

    def test_falls_back_to_content_data_uri(self, generator, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_msg = MagicMock()
        mock_msg.content = "data:image/png;base64,XYZ"
        mock_msg.images = []
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=mock_msg)]

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_resp
            mock_openai_cls.return_value = mock_client

            result = generator._generate_via_openrouter("prompt")

        assert result == "data:image/png;base64,XYZ"

    def test_returns_empty_on_missing_image(self, generator, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_msg = MagicMock()
        mock_msg.content = "just text no image"
        mock_msg.images = []
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=mock_msg)]

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_resp
            mock_openai_cls.return_value = mock_client

            result = generator._generate_via_openrouter("prompt")

        assert result == ""


class TestProviderDispatch:
    def test_raises_for_unknown_provider(self, config):
        config.provider = "unknown"
        gen = ImageGenerator(config, MagicMock())
        with pytest.raises(ValueError, match="Unknown image provider"):
            gen._generate_image("prompt")
