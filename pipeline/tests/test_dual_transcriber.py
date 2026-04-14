"""Tests for dual transcriber merge logic (SequenceMatcher-based merging)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pipeline.config import TranscriptionConfig
from pipeline.dual_transcriber import DualTranscriber


@pytest.fixture
def transcriber():
    config = TranscriptionConfig()
    session = MagicMock()
    return DualTranscriber(config, session)


class TestMergeLogic:
    def test_identical_words_preserve_whisper_timestamps(self, transcriber):
        """When primary and timestamped text match, use timestamps directly."""
        # Build a mock merged scenario by constructing Transcript objects
        episode = MagicMock()
        episode.id = 1

        primary = MagicMock()
        primary.full_text = "hello world"
        primary.id = 10

        timestamped = MagicMock()
        timestamped.words = [
            {"word": "hello", "start_ms": 0, "end_ms": 500},
            {"word": "world", "start_ms": 500, "end_ms": 1000},
        ]
        timestamped.id = 11

        # Mock the db.add to capture what's added
        added = []
        transcriber.db.add = lambda x: added.append(x)
        transcriber.db.flush = lambda: None

        result = transcriber._merge_transcripts(episode, primary, timestamped)

        assert result.words == [
            {"word": "hello", "start_ms": 0, "end_ms": 500},
            {"word": "world", "start_ms": 500, "end_ms": 1000},
        ]
        assert result.full_text == "hello world"
        assert result.transcript_type == "merged"
        assert result.provider == "merged"

    def test_replace_op_interpolates_timestamps(self, transcriber):
        """When primary has corrected spelling, interpolate within Whisper window."""
        episode = MagicMock()
        episode.id = 1
        primary = MagicMock()
        primary.full_text = "halacha one two"
        primary.id = 10

        timestamped = MagicMock()
        timestamped.words = [
            {"word": "halakah", "start_ms": 0, "end_ms": 300},  # misspelled by Whisper
            {"word": "won", "start_ms": 300, "end_ms": 600},
            {"word": "too", "start_ms": 600, "end_ms": 900},
        ]
        timestamped.id = 11

        added = []
        transcriber.db.add = lambda x: added.append(x)
        transcriber.db.flush = lambda: None

        result = transcriber._merge_transcripts(episode, primary, timestamped)

        # All 3 primary words should appear with some timestamp
        assert len(result.words) == 3
        assert [w["word"] for w in result.words] == ["halacha", "one", "two"]
        # Timestamps should be monotonically non-decreasing
        for i in range(len(result.words) - 1):
            assert result.words[i]["start_ms"] <= result.words[i + 1]["start_ms"]

    def test_empty_inputs_produce_empty_merge(self, transcriber):
        episode = MagicMock()
        episode.id = 1
        primary = MagicMock()
        primary.full_text = ""
        primary.id = 10
        timestamped = MagicMock()
        timestamped.words = []
        timestamped.id = 11

        added = []
        transcriber.db.add = lambda x: added.append(x)
        transcriber.db.flush = lambda: None

        result = transcriber._merge_transcripts(episode, primary, timestamped)

        assert result.words == []
        assert result.full_text == ""

    def test_insert_op_uses_last_end_ms(self, transcriber):
        """Words only in primary (missing from Whisper) get last_end_ms for both."""
        episode = MagicMock()
        episode.id = 1
        primary = MagicMock()
        primary.full_text = "one two three four"
        primary.id = 10

        timestamped = MagicMock()
        timestamped.words = [
            {"word": "one", "start_ms": 0, "end_ms": 100},
            {"word": "two", "start_ms": 100, "end_ms": 200},
        ]
        timestamped.id = 11

        added = []
        transcriber.db.add = lambda x: added.append(x)
        transcriber.db.flush = lambda: None

        result = transcriber._merge_transcripts(episode, primary, timestamped)

        words = result.words
        assert len(words) == 4
        # "three" and "four" are inserts — should have last_end_ms = 200
        three = next(w for w in words if w["word"] == "three")
        assert three["start_ms"] == 200
        assert three["end_ms"] == 200
