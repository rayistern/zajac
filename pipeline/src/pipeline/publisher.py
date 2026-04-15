"""Publisher: bridges approved pipeline artifacts into frontend content_items.

The pipeline writes to `artifacts` + `artifact_versions` tables. The frontend
(Hono API + React) reads from `content_item` + `learning_day`. This module
copies approved artifact_versions into content_items so the frontend can
display them.

Reads from pipeline DB via SQLAlchemy session. Writes to frontend DB via
separate psycopg2 connection (they live in different databases).
"""

from __future__ import annotations

import os
import uuid
from datetime import date
from typing import Any

import psycopg2
import structlog
from psycopg2.extras import Json
from sqlalchemy.orm import Session

from .db import Artifact, ArtifactVersion, SourceUnit

logger = structlog.get_logger()


# Map pipeline artifact subtype → frontend content_type.
#
# Must stay in sync with the CHECK constraint in
# pipeline/alembic/versions/002_phase_1_5_foundations.py
# (ck_artifacts_subtype_allowed). Adding a new subtype = new entry here
# AND new migration extending the allow-list.
SUBTYPE_TO_CONTENT_TYPE: dict[str, str] = {
    "illustration": "conceptual_image",
    "diagram": "conceptual_image",
    "infographic": "infographic",
    "chart": "daily_chart",
    "timeline": "daily_chart",
    "map": "conceptual_image",
    "quiz": "quiz",
}


def _parse_sefaria_ref(ref: str) -> tuple[str, int, int | None]:
    """Parse 'Mishneh Torah, Marriage 2:3' → ('Marriage', 2, 3).

    Returns (sefer, perek, halacha-or-None). Perek always present; halacha
    present only when the ref includes `:N`.
    """
    # Strip work prefix ("Mishneh Torah, ")
    work_split = ref.split(", ", 1)
    tail = work_split[1] if len(work_split) > 1 else work_split[0]

    # tail is like "Marriage 2:3" or "Marriage 2"
    if ":" in tail:
        book_perek, halacha_str = tail.rsplit(":", 1)
        halacha = int(halacha_str) if halacha_str.isdigit() else None
    else:
        book_perek = tail
        halacha = None

    # Split book name from perek number
    parts = book_perek.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0], int(parts[1]), halacha

    return book_perek, 1, halacha


class Publisher:
    def __init__(
        self,
        pipeline_session: Session,
        frontend_db_url: str | None = None,
    ):
        """Bridge pipeline → frontend content.

        frontend_db_url defaults to FRONTEND_DATABASE_URL env var, or builds
        a URL from DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASS (matching api/.env.dev).
        """
        self.pipeline_db = pipeline_session
        self.frontend_db_url = frontend_db_url or self._build_frontend_url()

    def _build_frontend_url(self) -> str:
        explicit = os.environ.get("FRONTEND_DATABASE_URL")
        if explicit:
            return explicit

        host = os.environ.get("DB_HOST", "127.0.0.1")
        port = os.environ.get("DB_PORT", "5432")
        db = os.environ.get("DB_NAME", "app")
        user = os.environ.get("DB_USER", "postgres")
        pw = os.environ.get("DB_PASS", "postgres")
        return f"postgresql://{user}:{pw}@{host}:{port}/{db}"

    def publish_approved(
        self,
        target_date: date | None = None,
        learning_day_perakim: dict[str, list[dict[str, Any]]] | None = None,
    ) -> int:
        """Copy all approved-but-not-yet-published artifact_versions to content_item.

        Args:
            target_date: the learning day to attach content to. Defaults to today.
            learning_day_perakim: track_1_perakim and track_3_perakim for
                creating a learning_day row if one doesn't exist. Falls back
                to an empty-perakim stub.

        Returns the number of content_items created.
        """
        if target_date is None:
            target_date = date.today()

        if learning_day_perakim is None:
            learning_day_perakim = {"track1": [], "track3": []}

        # Query approved versions that are the current version on their artifact
        # and haven't already been published
        approved = (
            self.pipeline_db.query(ArtifactVersion, Artifact, SourceUnit)
            .join(Artifact, ArtifactVersion.artifact_id == Artifact.id)
            .join(SourceUnit, Artifact.source_unit_id == SourceUnit.id)
            .filter(ArtifactVersion.status == "approved")
            .filter(Artifact.status.in_(["approved", "published"]))
            .filter(Artifact.current_version_id == ArtifactVersion.id)
            .all()
        )

        if not approved:
            logger.info("publisher.nothing_to_publish", target_date=str(target_date))
            return 0

        conn = psycopg2.connect(self.frontend_db_url)
        try:
            with conn.cursor() as cur:
                learning_day_id = self._ensure_learning_day(
                    cur, target_date, learning_day_perakim
                )
                created = 0
                for version, artifact, source_unit in approved:
                    if self._already_published(cur, version.id):
                        continue

                    content_type = SUBTYPE_TO_CONTENT_TYPE.get(
                        artifact.subtype or "illustration", "conceptual_image"
                    )
                    sefer, perek, halacha = _parse_sefaria_ref(source_unit.sefaria_ref)

                    self._insert_content_item(
                        cur,
                        learning_day_id=learning_day_id,
                        content_type=content_type,
                        sefer=sefer,
                        perek=perek,
                        halacha=halacha,
                        artifact=artifact,
                        version=version,
                    )

                    # Mark as published in pipeline DB so we don't re-publish
                    version.status = "published"
                    artifact.status = "published"
                    created += 1

            conn.commit()
            self.pipeline_db.flush()
            logger.info(
                "publisher.published",
                target_date=str(target_date),
                created=created,
            )
            return created
        finally:
            conn.close()

    def _ensure_learning_day(
        self,
        cur,
        target_date: date,
        perakim: dict[str, list[dict[str, Any]]],
    ) -> str:
        """Find or create a learning_day row, return its id."""
        cur.execute(
            "SELECT id FROM learning_day WHERE date = %s", (target_date,)
        )
        row = cur.fetchone()
        if row:
            return row[0]

        new_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO learning_day (id, date, hebrew_date, track_1_perakim, track_3_perakim)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                new_id,
                target_date,
                None,
                Json(perakim.get("track1", [])),
                Json(perakim.get("track3", [])),
            ),
        )
        return new_id

    def _already_published(self, cur, version_id: int) -> bool:
        cur.execute(
            "SELECT 1 FROM content_item WHERE generation_model = %s LIMIT 1",
            (f"pipeline-v{version_id}",),
        )
        return cur.fetchone() is not None

    def _insert_content_item(
        self,
        cur,
        learning_day_id: str,
        content_type: str,
        sefer: str,
        perek: int,
        halacha: int | None,
        artifact: Artifact,
        version: ArtifactVersion,
    ) -> None:
        title = self._build_title(content_type, sefer, perek, halacha)
        content = self._build_content_json(version, content_type)

        cur.execute(
            """
            INSERT INTO content_item (
                id, learning_day_id, content_type, sefer, perek,
                halacha_start, halacha_end, title, content,
                image_url, status, generation_model, sort_order
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid.uuid4()),
                learning_day_id,
                content_type,
                sefer,
                perek,
                halacha,
                halacha,
                title,
                Json(content),
                version.url or "",
                "published",
                f"pipeline-v{version.id}",
                artifact.priority,
            ),
        )

    def _build_title(
        self, content_type: str, sefer: str, perek: int, halacha: int | None
    ) -> str:
        ref = f"{sefer} {perek}"
        if halacha is not None:
            ref = f"{ref}:{halacha}"
        if content_type == "conceptual_image":
            return f"Illustration — {ref}"
        if content_type == "infographic":
            return f"Infographic — {ref}"
        if content_type == "daily_chart":
            return f"Chart — {ref}"
        return ref

    def _build_content_json(
        self, version: ArtifactVersion, content_type: str
    ) -> dict[str, Any]:
        caption_parts: list[str] = []
        if version.generation_prompt:
            # Use the "Visual focus:" line as caption if present
            for line in version.generation_prompt.splitlines():
                if line.strip().lower().startswith("visual focus:"):
                    caption_parts.append(line.split(":", 1)[1].strip())
                    break
        return {
            "caption": " ".join(caption_parts) or "Generated by Merkos Rambam pipeline",
            "style": version.style_name or "",
        }
