"""
rss_parser.py — Fetch and parse podcast RSS feeds.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

from .logger import get_logger

log = get_logger(__name__)


@dataclass
class Episode:
    guid: str
    title: str
    audio_url: str
    feed_url: str
    published_at: datetime | None = None
    episode_number: int | None = None
    description: str = ""
    duration_seconds: int | None = None
    show_title: str = ""
    image_url: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        pub = self.published_at.date() if self.published_at else "unknown date"
        return f"<Episode #{self.episode_number} '{self.title}' ({pub})>"


def _derive_guid(entry: Any, feed_url: str) -> str:
    """Derive a stable GUID even if the feed doesn't provide one."""
    if hasattr(entry, "id") and entry.id:
        return entry.id
    # Fallback: hash of feed URL + title
    raw = f"{feed_url}::{entry.get('title', '')}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _parse_audio_url(entry: Any) -> str | None:
    """Extract the MP3/audio enclosure URL from a feed entry."""
    for link in getattr(entry, "enclosures", []):
        mime = getattr(link, "type", "") or ""
        if "audio" in mime or link.href.lower().endswith((".mp3", ".m4a", ".ogg", ".wav")):
            return link.href
    # Fallback: look in links
    for link in getattr(entry, "links", []):
        if "audio" in getattr(link, "type", ""):
            return link.href
    return None


def _parse_published(entry: Any) -> datetime | None:
    struct = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if struct:
        try:
            import calendar
            ts = calendar.timegm(struct)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass
    return None


def _parse_duration(entry: Any) -> int | None:
    """Return duration in seconds, or None."""
    itunes = getattr(entry, "itunes_duration", None)
    if itunes:
        parts = str(itunes).split(":")
        try:
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + int(s)
            elif len(parts) == 2:
                m, s = parts
                return int(m) * 60 + int(s)
            else:
                return int(parts[0])
        except ValueError:
            pass
    return None


class RSSParser:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.rss_cfg = cfg["rss"]

    def fetch_episodes(self, feed_url: str | None = None) -> list[Episode]:
        url = feed_url or self.rss_cfg["feed_url"]
        log.info(f"Fetching RSS feed: {url}")

        parsed = feedparser.parse(url)
        if parsed.bozo and not parsed.entries:
            raise ValueError(
                f"Failed to parse RSS feed '{url}': {parsed.bozo_exception}"
            )

        show_title = parsed.feed.get("title", "")
        show_image = parsed.feed.get("image", {}).get("href", "")

        episodes: list[Episode] = []
        max_eps = self.rss_cfg.get("max_episodes", 1)
        max_age = self.rss_cfg.get("max_age_days", 0)
        now = datetime.now(timezone.utc)

        for entry in parsed.entries[:max_eps * 5]:  # fetch extra to account for filtering
            audio_url = _parse_audio_url(entry)
            if not audio_url:
                log.debug(f"Skipping entry with no audio enclosure: {entry.get('title')}")
                continue

            published = _parse_published(entry)

            if max_age and published:
                age_days = (now - published).days
                if age_days > max_age:
                    log.debug(f"Skipping episode older than {max_age} days: {entry.get('title')}")
                    continue

            ep = Episode(
                guid=_derive_guid(entry, url),
                title=entry.get("title", "Untitled"),
                audio_url=audio_url,
                feed_url=url,
                published_at=published,
                episode_number=_parse_episode_number(entry),
                description=entry.get("summary", entry.get("description", "")),
                duration_seconds=_parse_duration(entry),
                show_title=show_title,
                image_url=show_image,
                raw=dict(entry),
            )
            episodes.append(ep)
            if len(episodes) >= max_eps:
                break

        log.info(f"Found {len(episodes)} episode(s) to process from '{show_title}'")
        return episodes


def _parse_episode_number(entry: Any) -> int | None:
    num = getattr(entry, "itunes_episode", None)
    if num:
        try:
            return int(num)
        except ValueError:
            pass
    return None
