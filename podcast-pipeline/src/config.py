"""
config.py — Load, merge, and validate YAML configuration + .env secrets.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

_CONFIG_CACHE: dict[str, Any] | None = None
_PROMPTS_CACHE: dict[str, Any] | None = None


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base* (override wins)."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    base_path = Path(config_path)
    if not base_path.exists():
        raise FileNotFoundError(f"Config file not found: {base_path.resolve()}")

    with base_path.open() as f:
        cfg = yaml.safe_load(f)

    # Optional local override file (gitignored)
    local_path = base_path.with_suffix(".local.yaml")
    if local_path.exists():
        with local_path.open() as f:
            local_cfg = yaml.safe_load(f) or {}
        cfg = _deep_merge(cfg, local_cfg)

    _CONFIG_CACHE = cfg
    return cfg


def load_prompts(prompts_path: str | None = None) -> dict[str, Any]:
    global _PROMPTS_CACHE
    if _PROMPTS_CACHE is not None:
        return _PROMPTS_CACHE

    cfg = load_config()
    path = Path(prompts_path or cfg["pipeline"]["prompts_file"])
    if not path.exists():
        raise FileNotFoundError(f"Prompts file not found: {path.resolve()}")

    with path.open() as f:
        prompts = yaml.safe_load(f)

    _PROMPTS_CACHE = prompts
    return prompts


def get_secret(name: str, required: bool = True) -> str | None:
    """Fetch a secret from environment variables."""
    value = os.environ.get(name)
    if required and not value:
        raise EnvironmentError(
            f"Required environment variable '{name}' is not set. "
            f"Check your .env file."
        )
    return value


def format_prompt(template: str, **kwargs: Any) -> str:
    """
    Fill a prompt template with kwargs.
    Template variables look like {key}; literal braces are {{ and }}.
    """
    return template.format(**kwargs)
