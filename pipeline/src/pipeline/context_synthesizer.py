"""Context synthesis: FULL vs SYNTHESIZED context modes for image prompts."""

from __future__ import annotations

import hashlib

import structlog
from sqlalchemy.orm import Session

from .db import Alignment, ContextSynthesis, SourceUnit, Transcript
from .llm import LLMClient

logger = structlog.get_logger()


class ContextSynthesizer:
    def __init__(self, model: str, session: Session):
        self.model = model
        self.db = session
        self.client = LLMClient(model)

    def get_context(
        self,
        source_unit: SourceUnit,
        transcript: Transcript | None = None,
        alignments: list[Alignment] | None = None,
        mode: str = "SYNTHESIZED",
        class_id: int | None = None,
    ) -> str:
        """Get context for image generation prompt construction.

        FULL mode: returns raw source text + transcript excerpt.
        SYNTHESIZED mode: returns LLM-condensed context (cached).
        """
        if mode == "FULL":
            return self._full_context(source_unit, transcript, alignments)
        return self._synthesized_context(source_unit, transcript, alignments, class_id)

    def _full_context(
        self,
        source_unit: SourceUnit,
        transcript: Transcript | None,
        alignments: list[Alignment] | None,
    ) -> str:
        parts = [f"Source text ({source_unit.sefaria_ref}):\n{source_unit.hebrew_text}"]

        if transcript and alignments:
            relevant = [a for a in alignments if a.source_unit_id == source_unit.id]
            if relevant and transcript.words:
                for al in relevant:
                    words = [
                        w for w in transcript.words
                        if (al.start_ms or 0) <= w["start_ms"] <= (al.end_ms or 0)
                    ]
                    if words:
                        excerpt = " ".join(w["word"] for w in words)
                        parts.append(f"Teacher's discussion:\n{excerpt[:1000]}")

        return "\n\n".join(parts)

    def _synthesized_context(
        self,
        source_unit: SourceUnit,
        transcript: Transcript | None,
        alignments: list[Alignment] | None,
        class_id: int | None,
    ) -> str:
        # Check cache
        input_text = self._full_context(source_unit, transcript, alignments)
        input_hash = hashlib.sha256(input_text.encode()).hexdigest()[:16]

        cached = (
            self.db.query(ContextSynthesis)
            .filter_by(source_unit_id=source_unit.id, class_id=class_id, input_hash=input_hash)
            .filter(ContextSynthesis.invalidated_at.is_(None))
            .first()
        )
        if cached:
            return cached.synthesis_text

        prompt = f"""Synthesize this Torah content into a concise context paragraph for
generating educational visual content. Focus on the key concepts, actions, and objects
that could be visually represented.

{input_text}

Write a 2-3 sentence synthesis in English that captures the visual essence of this halacha.
Focus on concrete, depictable elements. Do not include any Hebrew text in your response."""

        synthesis_text = self.client.complete(prompt, max_tokens=512).strip()

        synthesis = ContextSynthesis(
            source_unit_id=source_unit.id,
            class_id=class_id,
            synthesis_text=synthesis_text,
            llm_model=self.model,
            input_hash=input_hash,
        )
        self.db.add(synthesis)
        self.db.flush()

        logger.info(
            "synthesizer.created",
            ref=source_unit.sefaria_ref,
            hash=input_hash,
        )
        return synthesis_text
