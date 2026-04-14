"""Fetch and cache canonical Rambam text from Sefaria API."""

from __future__ import annotations

from datetime import datetime, timedelta

import httpx
import structlog
from sqlalchemy.orm import Session

from .config import SefariaConfig
from .db import SourceUnit, Work

logger = structlog.get_logger()

# Ashkenazic → Sefaria (Sephardic/English) name mapping for Rambam books.
# Chabad.org RSS feed uses Ashkenazic transliteration; Sefaria expects Sephardic.
RAMBAM_BOOK_ALIASES = {
    "Ishus": "Marriage",
    "Ishut": "Marriage",
    "Gerushin": "Divorce",
    "Yibum v'Chalitzah": "Levirate Marriage and Release",
    "Na'arah Besulah": "Virgin Maiden",
    "Sotah": "Sotah",
    "Issurei Biah": "Forbidden Intercourse",
    "Maachalos Asuros": "Forbidden Foods",
    "Shechitah": "Ritual Slaughter",
    "Shevuos": "Oaths",
    "Nedarim": "Vows",
    "Nezirus": "Nazariteship",
    "Shabbat": "Shabbat",
    "Shabbos": "Shabbat",
    "Eruvin": "Eruvin",
    "Megillah v'Chanukah": "Scroll of Esther and Hanukkah",
    "Ta'aniyos": "Fasts",
    "Kiddush HaChodesh": "Sanctification of the New Month",
    "Beis HaBechirah": "The Chosen House",
    "Klei HaMikdash": "Temple Vessels",
    "Biat HaMikdash": "Entrance into the Sanctuary",
    "Issurei Mizbe'ach": "Forbidden Altar Offerings",
    "Ma'aseh HaKorbanos": "Manner of Offering Sacrifices",
    "Temidin u'Musafin": "Daily Offerings and Additional Offerings",
    "Pesulei HaMukdashin": "Disqualified Consecrated Items",
    "Avodas Yom HaKippurim": "Service of Yom Kippur",
    "Me'ilah": "Trespass",
    # Add more as needed
}


def normalize_book_name(name: str) -> str:
    """Convert Ashkenazic/colloquial book name to Sefaria's canonical name."""
    return RAMBAM_BOOK_ALIASES.get(name, name)


class SefariaClient:
    def __init__(self, config: SefariaConfig, session: Session):
        self.config = config
        self.db = session
        self.http = httpx.Client(base_url=config.base_url, timeout=30)

    def get_or_create_work(self, sefaria_index_title: str) -> Work:
        """Get a work from DB or create it from Sefaria index metadata."""
        work = self.db.query(Work).filter_by(sefaria_index_title=sefaria_index_title).first()
        if work:
            return work

        resp = self.http.get(f"/v2/index/{sefaria_index_title}")
        resp.raise_for_status()
        meta = resp.json()

        # Rambam uses Book / Chapter / Halacha hierarchy
        address_types = meta.get("schema", {}).get("addressTypes", [])
        section_names = meta.get("schema", {}).get("sectionNames", [])

        work = Work(
            sefaria_index_title=sefaria_index_title,
            common_name=meta.get("title", sefaria_index_title),
            level_1_name=section_names[0] if len(section_names) > 0 else "Book",
            level_2_name=section_names[1] if len(section_names) > 1 else "Chapter",
            level_3_name=section_names[2] if len(section_names) > 2 else "Halacha",
            language=self.config.language,
            sefaria_metadata=meta,
        )
        self.db.add(work)
        self.db.flush()
        logger.info("sefaria.work_created", title=sefaria_index_title, work_id=work.id)
        return work

    def fetch_source_unit(
        self, work: Work, level_1: str, level_2: str, level_3: str
    ) -> SourceUnit:
        """Fetch a single source unit (halacha/verse) from Sefaria, caching in DB."""
        existing = (
            self.db.query(SourceUnit)
            .filter_by(work_id=work.id, level_1=level_1, level_2=level_2, level_3=level_3)
            .first()
        )

        if existing and self._is_cache_valid(existing):
            return existing

        sefaria_ref = f"{work.sefaria_index_title}, {level_1} {level_2}:{level_3}"
        resp = self.http.get(f"/texts/{sefaria_ref}", params={"lang": self.config.language})
        resp.raise_for_status()
        data = resp.json()

        hebrew_text = data.get("he", "")
        if isinstance(hebrew_text, list):
            hebrew_text = " ".join(hebrew_text)

        if existing:
            existing.hebrew_text = hebrew_text
            existing.fetched_at = datetime.utcnow()
            logger.info("sefaria.unit_refreshed", ref=sefaria_ref)
            return existing

        unit = SourceUnit(
            work_id=work.id,
            sefaria_ref=sefaria_ref,
            level_1=level_1,
            level_2=level_2,
            level_3=level_3,
            hebrew_text=hebrew_text,
        )
        self.db.add(unit)
        self.db.flush()
        logger.info("sefaria.unit_fetched", ref=sefaria_ref, unit_id=unit.id)
        return unit

    def fetch_perek(self, work: Work, level_1: str, level_2: str) -> list[SourceUnit]:
        """Fetch all source units for a chapter/perek."""
        sefaria_ref = f"{work.sefaria_index_title}, {level_1} {level_2}"
        resp = self.http.get(f"/texts/{sefaria_ref}", params={"lang": self.config.language})
        resp.raise_for_status()
        data = resp.json()

        he_texts = data.get("he", [])
        if isinstance(he_texts, str):
            he_texts = [he_texts]

        units = []
        for i, text in enumerate(he_texts, start=1):
            level_3 = str(i)
            if isinstance(text, list):
                text = " ".join(text)

            existing = (
                self.db.query(SourceUnit)
                .filter_by(work_id=work.id, level_1=level_1, level_2=level_2, level_3=level_3)
                .first()
            )

            if existing and self._is_cache_valid(existing):
                units.append(existing)
                continue

            if existing:
                existing.hebrew_text = text
                existing.fetched_at = datetime.utcnow()
                units.append(existing)
            else:
                unit_ref = f"{work.sefaria_index_title}, {level_1} {level_2}:{level_3}"
                unit = SourceUnit(
                    work_id=work.id,
                    sefaria_ref=unit_ref,
                    level_1=level_1,
                    level_2=level_2,
                    level_3=level_3,
                    hebrew_text=text,
                )
                self.db.add(unit)
                units.append(unit)

        self.db.flush()
        logger.info("sefaria.perek_fetched", ref=sefaria_ref, count=len(units))
        return units

    def _is_cache_valid(self, unit: SourceUnit) -> bool:
        if not unit.fetched_at:
            return False
        return datetime.utcnow() - unit.fetched_at < timedelta(days=self.config.cache_ttl_days)

    def close(self):
        self.http.close()
