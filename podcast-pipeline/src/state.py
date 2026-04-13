"""
state.py — SQLite-backed state store to track processed episodes and chapters.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator


class StateDB:
    """Lightweight SQLite state store."""

    def __init__(self, db_path: str = "./pipeline_state.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS episodes (
                    guid            TEXT PRIMARY KEY,
                    feed_url        TEXT NOT NULL,
                    title           TEXT,
                    published_at    TEXT,
                    audio_url       TEXT,
                    local_audio     TEXT,
                    transcript_path TEXT,
                    status          TEXT DEFAULT 'pending',
                    error           TEXT,
                    processed_at    TEXT
                );

                CREATE TABLE IF NOT EXISTS chapters (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_guid    TEXT NOT NULL REFERENCES episodes(guid),
                    chapter_number  INTEGER NOT NULL,
                    title           TEXT,
                    summary         TEXT,
                    image_prompt    TEXT,
                    image_path      TEXT,
                    telegram_msg_id TEXT,
                    status          TEXT DEFAULT 'pending',
                    error           TEXT
                );
            """)

    # ------------------------------------------------------------------
    # Episodes
    # ------------------------------------------------------------------

    def is_episode_processed(self, guid: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT status FROM episodes WHERE guid = ?", (guid,)
            ).fetchone()
            return row is not None and row["status"] == "done"

    def upsert_episode(self, guid: str, **fields) -> None:
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT guid FROM episodes WHERE guid = ?", (guid,)
            ).fetchone()
            if existing:
                if fields:
                    set_clause = ", ".join(f"{k} = ?" for k in fields)
                    conn.execute(
                        f"UPDATE episodes SET {set_clause} WHERE guid = ?",
                        (*fields.values(), guid),
                    )
            else:
                fields["guid"] = guid
                cols = ", ".join(fields.keys())
                placeholders = ", ".join("?" * len(fields))
                conn.execute(
                    f"INSERT INTO episodes ({cols}) VALUES ({placeholders})",
                    tuple(fields.values()),
                )

    def mark_episode_done(self, guid: str) -> None:
        self.upsert_episode(
            guid,
            status="done",
            processed_at=datetime.now(timezone.utc).isoformat(),
        )

    def mark_episode_error(self, guid: str, error: str) -> None:
        self.upsert_episode(guid, status="error", error=error)

    # ------------------------------------------------------------------
    # Chapters
    # ------------------------------------------------------------------

    def save_chapter(self, episode_guid: str, chapter_number: int, **fields) -> int:
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM chapters WHERE episode_guid = ? AND chapter_number = ?",
                (episode_guid, chapter_number),
            ).fetchone()
            if existing:
                row_id = existing["id"]
                if fields:
                    set_clause = ", ".join(f"{k} = ?" for k in fields)
                    conn.execute(
                        f"UPDATE chapters SET {set_clause} WHERE id = ?",
                        (*fields.values(), row_id),
                    )
                return row_id
            else:
                fields.update(episode_guid=episode_guid, chapter_number=chapter_number)
                cols = ", ".join(fields.keys())
                placeholders = ", ".join("?" * len(fields))
                cursor = conn.execute(
                    f"INSERT INTO chapters ({cols}) VALUES ({placeholders})",
                    tuple(fields.values()),
                )
                return cursor.lastrowid

    def get_chapters(self, episode_guid: str) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM chapters WHERE episode_guid = ? ORDER BY chapter_number",
                (episode_guid,),
            ).fetchall()
