"""
logger.py — Centralised logging setup with Rich console output.
"""

import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler


_console = Console()
_configured = False


def setup_logger(level: str = "INFO", log_file: str | None = None) -> logging.Logger:
    global _configured
    if _configured:
        return logging.getLogger("podcast_pipeline")

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [
        RichHandler(console=_console, rich_tracebacks=True, show_path=False),
    ]

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s")
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=numeric_level,
        handlers=handlers,
        format="%(message)s",
        datefmt="[%X]",
    )

    _configured = True
    return logging.getLogger("podcast_pipeline")


def get_logger(name: str = "podcast_pipeline") -> logging.Logger:
    return logging.getLogger(name)
