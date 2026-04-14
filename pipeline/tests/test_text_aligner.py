"""Tests for text aligner — JSON parsing and pass logic (no LLM calls)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pipeline.config import LLMConfig, TextAlignmentConfig
from pipeline.text_aligner import TextAligner


@pytest.fixture
def aligner(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    config = TextAlignmentConfig(llm=LLMConfig())
    session = MagicMock()
    return TextAligner(config, session)


class TestJSONParsing:
    def test_extracts_simple_array(self, aligner):
        result = aligner._parse_json_response('[{"level_3": "1"}]')
        assert result == [{"level_3": "1"}]

    def test_extracts_array_from_surrounding_text(self, aligner):
        response = 'Here is the result: [{"a": 1}, {"b": 2}] — done.'
        result = aligner._parse_json_response(response)
        assert result == [{"a": 1}, {"b": 2}]

    def test_returns_empty_for_invalid_json(self, aligner):
        result = aligner._parse_json_response("not valid json [{}")
        assert result == []

    def test_returns_empty_for_no_array(self, aligner):
        result = aligner._parse_json_response("just some text")
        assert result == []

    def test_handles_empty_string(self, aligner):
        assert aligner._parse_json_response("") == []

    def test_handles_nested_arrays(self, aligner):
        result = aligner._parse_json_response('[{"nested": [1, 2, 3]}]')
        assert result == [{"nested": [1, 2, 3]}]


class TestGapDetection:
    def test_returns_source_units_not_in_headers(self, aligner):
        headers = [{"level_3": "1"}, {"level_3": "3"}]
        source_units = [MagicMock(level_3="1"), MagicMock(level_3="2"),
                        MagicMock(level_3="3"), MagicMock(level_3="4")]
        gaps = aligner._pass_gap_detection(headers, source_units)
        gap_levels = sorted(g["level_3"] for g in gaps)
        assert gap_levels == ["2", "4"]

    def test_no_gaps_when_all_covered(self, aligner):
        headers = [{"level_3": "1"}, {"level_3": "2"}]
        source_units = [MagicMock(level_3="1"), MagicMock(level_3="2")]
        gaps = aligner._pass_gap_detection(headers, source_units)
        assert gaps == []

    def test_all_gaps_when_no_headers(self, aligner):
        headers = []
        source_units = [MagicMock(level_3="1"), MagicMock(level_3="2")]
        gaps = aligner._pass_gap_detection(headers, source_units)
        assert len(gaps) == 2

    def test_uses_halacha_ref_as_fallback(self, aligner):
        """When level_3 missing, falls back to halacha_ref from regex detection."""
        headers = [{"halacha_ref": "5"}]
        source_units = [MagicMock(level_3="5"), MagicMock(level_3="6")]
        gaps = aligner._pass_gap_detection(headers, source_units)
        assert [g["level_3"] for g in gaps] == ["6"]

    def test_marks_gaps_with_status(self, aligner):
        headers = []
        source_units = [MagicMock(level_3="1")]
        gaps = aligner._pass_gap_detection(headers, source_units)
        assert gaps[0]["status"] == "gap"
