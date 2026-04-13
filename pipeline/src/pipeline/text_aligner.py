"""4-pass LLM alignment: transcript segments → source units/halachot."""

from __future__ import annotations

import json
import re

import anthropic
import structlog
from sqlalchemy.orm import Session

from .config import TextAlignmentConfig
from .db import Alignment, SourceUnit, Transcript

logger = structlog.get_logger()


class TextAligner:
    def __init__(self, config: TextAlignmentConfig, session: Session):
        self.config = config
        self.db = session
        self.client = anthropic.Anthropic()
        self.model = config.llm.model

    def align(
        self,
        transcript: Transcript,
        source_units: list[SourceUnit],
    ) -> list[Alignment]:
        """Run 4-pass alignment of transcript to source units."""
        if not transcript.words:
            logger.warning("aligner.no_words", transcript_id=transcript.id)
            return []

        existing = (
            self.db.query(Alignment)
            .filter_by(transcript_id=transcript.id)
            .all()
        )
        if existing:
            logger.info("aligner.cached", transcript_id=transcript.id, count=len(existing))
            return existing

        # Build source unit reference text
        source_ref = "\n".join(
            f"[{su.sefaria_ref}] (level_3={su.level_3}): {su.hebrew_text[:200]}"
            for su in source_units
        )

        # Pass 1: Header detection
        headers = self._pass_header_detection(transcript, source_units)
        logger.info("aligner.pass1_headers", count=len(headers))

        # Pass 2: Gap detection
        gaps = self._pass_gap_detection(headers, source_units)
        logger.info("aligner.pass2_gaps", count=len(gaps))

        # Pass 3: Content matching
        alignments_raw = self._pass_content_matching(transcript, source_units, headers)
        logger.info("aligner.pass3_matches", count=len(alignments_raw))

        # Pass 4: Verification
        verified = self._pass_verification(transcript, source_units, alignments_raw)
        logger.info("aligner.pass4_verified", count=len(verified))

        # Persist alignments
        alignments = []
        for item in verified:
            su = next(
                (su for su in source_units if su.level_3 == str(item.get("level_3", ""))),
                None,
            )
            if not su:
                continue

            alignment = Alignment(
                episode_id=transcript.episode_id,
                source_unit_id=su.id,
                transcript_id=transcript.id,
                start_ms=item.get("start_ms"),
                end_ms=item.get("end_ms"),
                confidence_score=item.get("confidence", 0.0),
                alignment_method=item.get("method", "content_match"),
                is_primary_reference=item.get("is_primary", True),
                is_digression=item.get("is_digression", False),
            )
            self.db.add(alignment)
            alignments.append(alignment)

        self.db.flush()
        logger.info("aligner.complete", transcript_id=transcript.id, count=len(alignments))
        return alignments

    def _pass_header_detection(
        self, transcript: Transcript, source_units: list[SourceUnit]
    ) -> list[dict]:
        """Pass 1: Detect explicit halacha headers in the transcript."""
        words = transcript.words or []
        full_text = transcript.full_text or ""

        # Regex scan for spoken headers like "הלכה ט" or "halacha 9"
        header_pattern = re.compile(
            r'(?:הלכה|הל[\'"]|halacha|halach[ao])\s*([א-תa-z0-9]+)',
            re.IGNORECASE,
        )

        regex_headers = []
        for match in header_pattern.finditer(full_text):
            regex_headers.append({
                "text": match.group(0),
                "halacha_ref": match.group(1),
                "char_offset": match.start(),
            })

        # LLM scan for less obvious headers
        prompt = f"""Analyze this Hebrew Torah class transcript and find all explicit mentions
where the teacher announces moving to a new halacha or section.

Transcript (first 3000 chars):
{full_text[:3000]}

Available source units:
{chr(10).join(f"- level_3={su.level_3}: {su.sefaria_ref}" for su in source_units)}

Return JSON array of detected headers:
[{{"text": "quoted text", "level_3": "number", "approximate_position_pct": 0.0-1.0}}]

Only return headers you are confident about. Return [] if none found."""

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        llm_headers = self._parse_json_response(resp.content[0].text)

        # Merge regex and LLM results
        headers = []
        for h in regex_headers:
            headers.append({"source": "regex", **h})
        for h in llm_headers:
            headers.append({"source": "llm", **h})

        return headers

    def _pass_gap_detection(
        self, headers: list[dict], source_units: list[SourceUnit]
    ) -> list[dict]:
        """Pass 2: Find source units not covered by any header."""
        detected = {str(h.get("level_3", h.get("halacha_ref", ""))) for h in headers}
        all_levels = {su.level_3 for su in source_units}
        missing = all_levels - detected
        return [{"level_3": m, "status": "gap"} for m in sorted(missing)]

    def _pass_content_matching(
        self,
        transcript: Transcript,
        source_units: list[SourceUnit],
        headers: list[dict],
    ) -> list[dict]:
        """Pass 3: Semantic alignment of transcript segments to source units."""
        words = transcript.words or []
        full_text = transcript.full_text or ""

        source_ref = "\n\n".join(
            f"=== Source Unit level_3={su.level_3} ({su.sefaria_ref}) ===\n{su.hebrew_text[:500]}"
            for su in source_units
        )

        prompt = f"""You are aligning a Hebrew Torah class transcript to canonical source text.

The teacher is discussing the following halachot in order (possibly skipping some):
{source_ref}

Transcript text (may be truncated):
{full_text[:6000]}

Previously detected headers: {json.dumps(headers, ensure_ascii=False)}

For each source unit that appears in the transcript, identify:
1. The approximate start and end position as percentage (0.0-1.0) of the transcript
2. Confidence score (0.0-1.0)
3. Whether this is the primary discussion or a digression/cross-reference

Return JSON array:
[{{
  "level_3": "halacha number",
  "start_pct": 0.0,
  "end_pct": 1.0,
  "confidence": 0.9,
  "is_primary": true,
  "is_digression": false,
  "method": "content_match"
}}]"""

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        matches = self._parse_json_response(resp.content[0].text)

        # Convert percentages to milliseconds
        if words:
            total_ms = words[-1]["end_ms"]
        else:
            total_ms = 0

        for m in matches:
            m["start_ms"] = int(m.get("start_pct", 0) * total_ms)
            m["end_ms"] = int(m.get("end_pct", 1) * total_ms)

        return matches

    def _pass_verification(
        self,
        transcript: Transcript,
        source_units: list[SourceUnit],
        alignments: list[dict],
    ) -> list[dict]:
        """Pass 4: LLM holistic review and confidence adjustment."""
        if not alignments:
            return []

        prompt = f"""Review these transcript-to-source alignments for correctness.

Source units available: {[su.level_3 for su in source_units]}

Proposed alignments:
{json.dumps(alignments, ensure_ascii=False, indent=2)}

Transcript excerpt:
{(transcript.full_text or "")[:3000]}

For each alignment, verify:
1. Does the timing make sense (sequential, no major overlaps)?
2. Is the confidence score reasonable?
3. Are primary/digression flags correct?

Return the corrected JSON array with the same structure. Adjust confidence scores
and flags as needed. Remove any alignments that are clearly wrong."""

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json_response(resp.content[0].text)

    def _parse_json_response(self, text: str) -> list[dict]:
        """Extract JSON array from LLM response text."""
        # Try to find JSON array in the response
        text = text.strip()
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        logger.warning("aligner.json_parse_failed", text=text[:200])
        return []
