"""Configuration loader with per-class override merging."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"


class TranscriptionConfig(BaseModel):
    primary_provider: str = "sofer_ai"
    # "openai_whisper" requires OPENAI_API_KEY; "synthetic" estimates
    # timestamps by distributing words proportionally across the audio.
    timestamp_provider: str = "synthetic"


class SefariaConfig(BaseModel):
    base_url: str = "https://www.sefaria.org/api"
    language: str = "he"
    cache_ttl_days: int = 30


class TextAlignmentConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)


class ArtifactPlanningConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    max_artifacts_per_source_unit: int = 5
    context_mode: str = "SYNTHESIZED"


class StylesConfig(BaseModel):
    enabled: list[str] = Field(
        default_factory=lambda: [
            "photorealistic", "watercolor", "cartoon", "line_art", "oil_painting"
        ]
    )
    rotation: str = "random_per_image"
    default: str = "photorealistic"


class ReplicateConfig(BaseModel):
    model: str = "black-forest-labs/flux-1.1-pro"


class OpenRouterImageConfig(BaseModel):
    model: str = "google/gemini-2.5-flash-image"


class ImageGenerationConfig(BaseModel):
    provider: str = "openrouter"  # "openrouter" or "replicate"
    openrouter: OpenRouterImageConfig = Field(default_factory=OpenRouterImageConfig)
    replicate: ReplicateConfig = Field(default_factory=ReplicateConfig)
    styles: StylesConfig = Field(default_factory=StylesConfig)


class TelegramConfig(BaseModel):
    bot_token: str = ""
    voting_group_chat_id: str = ""
    upvote_emoji: str = "\U0001F44D"
    downvote_emoji: str = "\U0001F44E"
    voting_window_hours: int = 24


class ApprovalConfig(BaseModel):
    min_approval_percentage: int = 70
    min_total_votes: int = 3


class WhatsAppConfig(BaseModel):
    rate_limit_per_second: int = 20
    max_retries: int = 3


class PipelineSettings(BaseModel):
    log_level: str = "INFO"
    log_format: str = "json"


class Config(BaseModel):
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    sefaria: SefariaConfig = Field(default_factory=SefariaConfig)
    text_alignment: TextAlignmentConfig = Field(default_factory=TextAlignmentConfig)
    artifact_planning: ArtifactPlanningConfig = Field(default_factory=ArtifactPlanningConfig)
    image_generation: ImageGenerationConfig = Field(default_factory=ImageGenerationConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    approval: ApprovalConfig = Field(default_factory=ApprovalConfig)
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)
    database_url: str = ""


def _resolve_env_vars(data: Any) -> Any:
    """Recursively resolve ${ENV_VAR} references in config values."""
    if isinstance(data, str) and data.startswith("${") and data.endswith("}"):
        return os.environ.get(data[2:-1], "")
    if isinstance(data, dict):
        return {k: _resolve_env_vars(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_resolve_env_vars(v) for v in data]
    return data


def load_config(path: str | Path | None = None) -> Config:
    """Load pipeline config from YAML, resolving env vars."""
    if path is None:
        path = Path(__file__).parent.parent.parent / "config.yaml"
    path = Path(path)

    if not path.exists():
        return Config()

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    resolved = _resolve_env_vars(raw)

    if "database_url" not in resolved:
        resolved["database_url"] = os.environ.get("DATABASE_URL", "")

    telegram = resolved.get("telegram", {})
    if not telegram.get("bot_token"):
        telegram["bot_token"] = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not telegram.get("voting_group_chat_id"):
        telegram["voting_group_chat_id"] = os.environ.get("TELEGRAM_VOTING_CHAT_ID", "")
    resolved["telegram"] = telegram

    return Config.model_validate(resolved)
