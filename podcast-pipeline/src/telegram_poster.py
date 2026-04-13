"""
telegram_poster.py — Post chapter images and captions to a Telegram group/channel.
"""

from __future__ import annotations

import time
from pathlib import Path

import requests

from .chapter_splitter import Chapter
from .config import get_secret, load_prompts, format_prompt
from .logger import get_logger
from .rss_parser import Episode

log = get_logger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramPoster:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.tg_cfg = cfg["telegram"]
        self.token = get_secret("TELEGRAM_BOT_TOKEN")
        self.chat_id = get_secret("TELEGRAM_CHAT_ID")
        self.prompts = load_prompts()
        self.parse_mode = self.tg_cfg.get("parse_mode", "HTML")
        self.delay = self.tg_cfg.get("message_delay_seconds", 2)
        self.max_caption = self.tg_cfg.get("max_caption_length", 900)
        self.send_mode = self.tg_cfg.get("send_mode", "per_chapter")
        self.include_header = self.tg_cfg.get("include_episode_header", True)
        self.disable_preview = self.tg_cfg.get("disable_web_page_preview", True)

    def _api_url(self, method: str) -> str:
        return TELEGRAM_API.format(token=self.token, method=method)

    def _send_photo(self, image_path: Path, caption: str) -> dict:
        caption = caption[: self.max_caption]
        with image_path.open("rb") as photo:
            resp = requests.post(
                self._api_url("sendPhoto"),
                data={
                    "chat_id": self.chat_id,
                    "caption": caption,
                    "parse_mode": self.parse_mode,
                    "disable_notification": False,
                },
                files={"photo": photo},
            )
        resp.raise_for_status()
        return resp.json()

    def _send_message(self, text: str) -> dict:
        resp = requests.post(
            self._api_url("sendMessage"),
            json={
                "chat_id": self.chat_id,
                "text": text[: 4096],
                "parse_mode": self.parse_mode,
                "disable_web_page_preview": self.disable_preview,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def post_chapter(
        self,
        chapter: Chapter,
        image_path: Path | None,
        episode: Episode,
        total_chapters: int,
    ) -> str | None:
        """Post a single chapter. Returns Telegram message_id."""
        caption = format_prompt(
            self.prompts["telegram"]["chapter_message"],
            podcast_title=episode.show_title,
            episode_title=episode.title,
            chapter_number=chapter.number,
            chapter_total=total_chapters,
            chapter_title=chapter.title,
            chapter_summary=chapter.summary,
        )

        try:
            if image_path and image_path.exists():
                result = self._send_photo(image_path, caption)
            else:
                log.warning(f"No image for chapter {chapter.number}, sending text only.")
                result = self._send_message(caption)

            msg_id = str(result["result"]["message_id"])
            log.info(f"Posted chapter {chapter.number} to Telegram (msg_id={msg_id})")
            time.sleep(self.delay)
            return msg_id

        except Exception as exc:
            log.error(f"Failed to post chapter {chapter.number}: {exc}")
            return None

    def post_episode_summary(
        self,
        chapters: list[Chapter],
        images: list[Path | None],
        episode: Episode,
    ) -> None:
        """Post a consolidated episode summary (all images in one media group + text)."""
        total = len(chapters)

        # Send intro text
        intro = format_prompt(
            self.prompts["telegram"]["episode_summary_intro"],
            podcast_title=episode.show_title,
            episode_title=episode.title,
            chapter_total=total,
        )
        self._send_message(intro)
        time.sleep(self.delay)

        # Send images as a media group (max 10 per group)
        valid_images = [(ch, img) for ch, img in zip(chapters, images) if img and img.exists()]

        for batch_start in range(0, len(valid_images), 10):
            batch = valid_images[batch_start: batch_start + 10]
            if len(batch) == 1:
                chapter, img = batch[0]
                caption = format_prompt(
                    self.prompts["telegram"]["episode_summary_chapter"],
                    chapter_number=chapter.number,
                    chapter_title=chapter.title,
                    chapter_summary=chapter.summary,
                )
                self._send_photo(img, caption)
            else:
                self._send_media_group(batch)
            time.sleep(self.delay)

    def _send_media_group(self, items: list[tuple[Chapter, Path]]) -> None:
        """Send up to 10 images as a Telegram media group."""
        media = []
        files = {}

        for i, (chapter, img_path) in enumerate(items):
            key = f"photo_{i}"
            caption = f"<b>{chapter.number}. {chapter.title}</b>\n{chapter.summary}"
            media.append({
                "type": "photo",
                "media": f"attach://{key}",
                "caption": caption[: self.max_caption],
                "parse_mode": self.parse_mode,
            })
            files[key] = open(img_path, "rb")

        try:
            import json
            resp = requests.post(
                self._api_url("sendMediaGroup"),
                data={
                    "chat_id": self.chat_id,
                    "media": json.dumps(media),
                },
                files=files,
            )
            resp.raise_for_status()
        finally:
            for f in files.values():
                f.close()
