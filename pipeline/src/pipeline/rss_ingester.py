"""RSS feed ingestion: discover new episodes from podcast feeds."""

from __future__ import annotations

import hashlib
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree

import httpx
import structlog
from sqlalchemy.orm import Session

from .db import Class, Episode

logger = structlog.get_logger()

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".ogg", ".wav", ".aac"}
AUDIO_MIMES = {"audio/mpeg", "audio/mp4", "audio/ogg", "audio/wav", "audio/aac", "audio/x-m4a"}


class RSSIngester:
    def __init__(self, session: Session, download_dir: str | None = None):
        self.db = session
        self.download_dir = download_dir or os.environ.get(
            "AUDIO_DOWNLOAD_DIR", tempfile.gettempdir()
        )
        self.http = httpx.Client(timeout=30, follow_redirects=True)

    def ingest_class(
        self,
        klass: Class,
        max_episodes: int = 5,
        max_age_days: int | None = None,
    ) -> list[Episode]:
        """Fetch RSS feed for a class and create Episode records for new entries."""
        if not klass.rss_feed_url:
            logger.warning("rss.no_feed_url", class_id=klass.id)
            return []

        resp = self.http.get(klass.rss_feed_url)
        resp.raise_for_status()

        root = ElementTree.fromstring(resp.text)
        channel = root.find("channel")
        if channel is None:
            logger.warning("rss.no_channel", class_id=klass.id)
            return []

        items = channel.findall("item")
        cutoff = None
        if max_age_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        new_episodes = []
        for item in items[:max_episodes * 5]:  # fetch extra to account for filtering
            if len(new_episodes) >= max_episodes:
                break

            guid = self._extract_guid(item, klass.rss_feed_url)
            existing = self.db.query(Episode).filter_by(guid=guid).first()
            if existing:
                continue

            audio_url = self._extract_audio_url(item)
            if not audio_url:
                continue

            pub_date = self._parse_pub_date(item)
            if cutoff and pub_date and pub_date < cutoff:
                continue

            title = self._text(item, "title")

            episode = Episode(
                guid=guid,
                class_id=klass.id,
                title=title,
                audio_url=audio_url,
                published_at=pub_date,
                status="pending",
            )
            self.db.add(episode)
            new_episodes.append(episode)

        self.db.flush()
        logger.info(
            "rss.ingested",
            class_id=klass.id,
            new_episodes=len(new_episodes),
        )
        return new_episodes

    def download_audio(self, episode: Episode) -> str | None:
        """Download episode audio to local disk. Returns local path."""
        if not episode.audio_url:
            return None

        if episode.local_audio_path and Path(episode.local_audio_path).exists():
            return episode.local_audio_path

        ext = Path(episode.audio_url.split("?")[0]).suffix or ".mp3"
        filename = f"episode_{episode.id}{ext}"
        local_path = os.path.join(self.download_dir, filename)

        logger.info("rss.downloading", episode_id=episode.id, url=episode.audio_url[:80])

        with self.http.stream("GET", episode.audio_url) as resp:
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)

        episode.local_audio_path = local_path
        self.db.flush()

        logger.info("rss.downloaded", episode_id=episode.id, path=local_path)
        return local_path

    def ingest_all_classes(
        self,
        max_episodes: int = 5,
        max_age_days: int | None = None,
    ) -> list[Episode]:
        """Ingest new episodes from all active classes."""
        classes = self.db.query(Class).filter_by(status="active").all()
        all_episodes = []
        for klass in classes:
            try:
                episodes = self.ingest_class(klass, max_episodes, max_age_days)
                all_episodes.extend(episodes)
            except Exception as e:
                logger.error("rss.class_failed", class_id=klass.id, error=str(e))
        return all_episodes

    def _extract_guid(self, item: ElementTree.Element, feed_url: str) -> str:
        guid_el = item.find("guid")
        if guid_el is not None and guid_el.text:
            return guid_el.text.strip()
        title = self._text(item, "title") or ""
        return hashlib.sha256(f"{feed_url}:{title}".encode()).hexdigest()[:32]

    def _extract_audio_url(self, item: ElementTree.Element) -> str | None:
        for enclosure in item.findall("enclosure"):
            mime = enclosure.get("type", "")
            url = enclosure.get("url", "")
            if mime in AUDIO_MIMES or any(url.lower().endswith(ext) for ext in AUDIO_EXTENSIONS):
                return url

        for link in item.findall("link"):
            url = link.text or link.get("href", "")
            if any(url.lower().endswith(ext) for ext in AUDIO_EXTENSIONS):
                return url

        return None

    def _parse_pub_date(self, item: ElementTree.Element) -> datetime | None:
        pub = self._text(item, "pubDate")
        if not pub:
            return None
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(pub)
        except Exception:
            return None

    def _text(self, el: ElementTree.Element, tag: str) -> str | None:
        child = el.find(tag)
        return child.text.strip() if child is not None and child.text else None

    def close(self):
        self.http.close()
