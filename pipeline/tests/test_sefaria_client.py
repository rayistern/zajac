"""Tests for Sefaria client — mapping and pure logic only (no live API calls)."""

from __future__ import annotations

import pytest

from pipeline.sefaria_client import (
    RAMBAM_BOOK_ALIASES,
    normalize_book_name,
)


class TestBookNameMapping:
    def test_maps_ashkenazic_ishus_to_marriage(self):
        assert normalize_book_name("Ishus") == "Marriage"

    def test_maps_sephardic_ishut_to_marriage(self):
        assert normalize_book_name("Ishut") == "Marriage"

    def test_maps_shabbos_to_shabbat(self):
        assert normalize_book_name("Shabbos") == "Shabbat"

    def test_maps_taaniyos_to_fasts(self):
        assert normalize_book_name("Ta'aniyos") == "Fasts"

    def test_maps_beis_habechirah_to_chosen_house(self):
        assert normalize_book_name("Beis HaBechirah") == "The Chosen House"

    def test_passes_through_unknown_names(self):
        # If not in the mapping, pass through unchanged
        assert normalize_book_name("Genesis") == "Genesis"
        assert normalize_book_name("Made Up Name") == "Made Up Name"

    def test_already_canonical_names_unchanged(self):
        # Sefaria's canonical English names shouldn't be re-mapped
        assert normalize_book_name("Marriage") == "Marriage"

    def test_preserves_case(self):
        assert normalize_book_name("ishus") == "ishus"  # lowercase not in mapping
        assert normalize_book_name("ISHUS") == "ISHUS"

    def test_mapping_covers_main_rambam_books(self):
        # Sanity check — the mapping should cover the books in the Chabad.org
        # daily Rambam 3-perek feed
        required = [
            "Ishus",
            "Gerushin",
            "Shabbos",
            "Shabbat",
            "Beis HaBechirah",
            "Kiddush HaChodesh",
            "Megillah v'Chanukah",
            "Ta'aniyos",
        ]
        for name in required:
            assert name in RAMBAM_BOOK_ALIASES, f"Missing mapping for {name}"
