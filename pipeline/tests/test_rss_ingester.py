"""Tests for RSS ingester — XML parsing and URL extraction (no network)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock
from xml.etree import ElementTree

import pytest

from pipeline.rss_ingester import (
    AUDIO_EXTENSIONS,
    AUDIO_MIMES,
    RSSIngester,
)


@pytest.fixture
def ingester():
    session = MagicMock()
    return RSSIngester(session)


def make_item(xml: str) -> ElementTree.Element:
    return ElementTree.fromstring(f"<item>{xml}</item>")


class TestGUIDExtraction:
    def test_uses_guid_element_when_present(self, ingester):
        item = make_item("<guid>unique-guid-123</guid>")
        assert ingester._extract_guid(item, "http://feed") == "unique-guid-123"

    def test_falls_back_to_sha256_hash_when_no_guid(self, ingester):
        item = make_item("<title>Episode Title</title>")
        guid = ingester._extract_guid(item, "http://feed.com/rss")
        assert len(guid) == 32
        # Should be deterministic
        guid2 = ingester._extract_guid(item, "http://feed.com/rss")
        assert guid == guid2

    def test_different_feed_urls_produce_different_guids(self, ingester):
        item = make_item("<title>Same Title</title>")
        guid1 = ingester._extract_guid(item, "http://feed1.com")
        guid2 = ingester._extract_guid(item, "http://feed2.com")
        assert guid1 != guid2

    def test_strips_whitespace(self, ingester):
        item = make_item("<guid>  padded-guid  </guid>")
        assert ingester._extract_guid(item, "http://feed") == "padded-guid"


class TestAudioURLExtraction:
    def test_finds_mp3_enclosure_by_mime(self, ingester):
        item = make_item(
            '<enclosure url="http://host/a.mp3" type="audio/mpeg"/>'
        )
        assert ingester._extract_audio_url(item) == "http://host/a.mp3"

    def test_finds_m4a_enclosure_by_mime(self, ingester):
        item = make_item(
            '<enclosure url="http://host/a.m4a" type="audio/mp4"/>'
        )
        assert ingester._extract_audio_url(item) == "http://host/a.m4a"

    def test_finds_url_by_extension_when_mime_missing(self, ingester):
        item = make_item(
            '<enclosure url="http://host/a.mp3" type="unknown"/>'
        )
        assert ingester._extract_audio_url(item) == "http://host/a.mp3"

    def test_returns_none_for_non_audio_enclosure(self, ingester):
        item = make_item(
            '<enclosure url="http://host/a.jpg" type="image/jpeg"/>'
        )
        assert ingester._extract_audio_url(item) is None

    def test_returns_none_when_no_enclosure(self, ingester):
        item = make_item("<title>No audio</title>")
        assert ingester._extract_audio_url(item) is None

    def test_prefers_enclosure_over_link(self, ingester):
        item = make_item(
            '<enclosure url="http://host/a.mp3" type="audio/mpeg"/>'
            '<link>http://host/b.mp3</link>'
        )
        assert ingester._extract_audio_url(item) == "http://host/a.mp3"


class TestPubDateParsing:
    def test_parses_rfc2822_date(self, ingester):
        item = make_item("<pubDate>Mon, 13 Apr 2026 17:00:00 +0000</pubDate>")
        date = ingester._parse_pub_date(item)
        assert date is not None
        assert date.year == 2026
        assert date.month == 4
        assert date.day == 13

    def test_returns_none_for_missing_date(self, ingester):
        item = make_item("<title>No date</title>")
        assert ingester._parse_pub_date(item) is None

    def test_returns_none_for_invalid_date(self, ingester):
        item = make_item("<pubDate>not a date</pubDate>")
        assert ingester._parse_pub_date(item) is None


class TestTextExtraction:
    def test_extracts_text_from_element(self, ingester):
        item = make_item("<title>My Title</title>")
        assert ingester._text(item, "title") == "My Title"

    def test_strips_whitespace(self, ingester):
        item = make_item("<title>  spaced  </title>")
        assert ingester._text(item, "title") == "spaced"

    def test_returns_none_for_missing_tag(self, ingester):
        item = make_item("<title>Only title</title>")
        assert ingester._text(item, "description") is None

    def test_returns_none_for_empty_tag(self, ingester):
        item = make_item("<title></title>")
        assert ingester._text(item, "title") is None


class TestConstants:
    def test_audio_extensions_complete(self):
        assert ".mp3" in AUDIO_EXTENSIONS
        assert ".m4a" in AUDIO_EXTENSIONS
        assert ".ogg" in AUDIO_EXTENSIONS
        assert ".wav" in AUDIO_EXTENSIONS

    def test_audio_mimes_complete(self):
        assert "audio/mpeg" in AUDIO_MIMES
        assert "audio/mp4" in AUDIO_MIMES
