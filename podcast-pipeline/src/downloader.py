"""
downloader.py — Download podcast audio files with retry and progress tracking.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, before_log
import logging

from .logger import get_logger

log = get_logger(__name__)


class Downloader:
    def __init__(self, cfg: dict) -> None:
        self.dl_cfg = cfg["download"]
        self.output_dir = Path(self.dl_cfg["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = self.dl_cfg.get("max_size_mb", 500) * 1_000_000
        self.retries = self.dl_cfg.get("retries", 3)
        self.retry_delay = self.dl_cfg.get("retry_delay_seconds", 5)

    def _filename_from_url(self, url: str, episode_guid: str) -> str:
        parsed = urlparse(url)
        name = Path(parsed.path).name
        if not name or "." not in name:
            name = f"{episode_guid}.mp3"
        # Sanitise
        name = "".join(c if c.isalnum() or c in ".-_" else "_" for c in name)
        return name

    def download(self, url: str, episode_guid: str) -> Path:
        """
        Download audio from *url* and return the local file path.
        Skips download if the file already exists.
        """
        filename = self._filename_from_url(url, episode_guid)
        dest = self.output_dir / filename

        if dest.exists():
            log.info(f"Audio already downloaded: {dest}")
            return dest

        log.info(f"Downloading audio → {dest}")
        self._download_with_retry(url, dest)
        return dest

    def _download_with_retry(self, url: str, dest: Path) -> None:
        for attempt in range(1, self.retries + 1):
            try:
                self._stream_download(url, dest)
                return
            except Exception as exc:
                log.warning(f"Download attempt {attempt}/{self.retries} failed: {exc}")
                if attempt < self.retries:
                    time.sleep(self.retry_delay * attempt)
                else:
                    raise RuntimeError(
                        f"Failed to download {url} after {self.retries} attempts"
                    ) from exc

    def _stream_download(self, url: str, dest: Path) -> None:
        headers = {"User-Agent": "PodcastPipeline/1.0"}
        tmp = dest.with_suffix(".tmp")

        with requests.get(url, stream=True, headers=headers, timeout=60) as resp:
            resp.raise_for_status()

            content_length = int(resp.headers.get("Content-Length", 0))
            if self.max_size_bytes and content_length > self.max_size_bytes:
                raise ValueError(
                    f"File size {content_length / 1e6:.1f} MB exceeds limit "
                    f"{self.max_size_bytes / 1e6:.0f} MB"
                )

            downloaded = 0
            chunk_size = 1024 * 256  # 256 KB

            with tmp.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if self.max_size_bytes and downloaded > self.max_size_bytes:
                            tmp.unlink(missing_ok=True)
                            raise ValueError(
                                f"Download exceeded max size {self.max_size_bytes / 1e6:.0f} MB"
                            )

        shutil.move(str(tmp), str(dest))
        size_mb = dest.stat().st_size / 1_000_000
        log.info(f"Download complete: {dest.name} ({size_mb:.1f} MB)")
