"""Dual transcription: sofer.ai (accuracy) + Whisper (timestamps) → merge."""

from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path

import httpx
import structlog
from sqlalchemy.orm import Session

from .config import TranscriptionConfig
from .db import Episode, Transcript

logger = structlog.get_logger()


class DualTranscriber:
    def __init__(self, config: TranscriptionConfig, session: Session):
        self.config = config
        self.db = session

    def transcribe(self, episode: Episode, audio_path: str) -> Transcript:
        """Run dual transcription and merge results."""
        existing = (
            self.db.query(Transcript)
            .filter_by(episode_id=episode.id, transcript_type="merged")
            .first()
        )
        if existing:
            logger.info("transcriber.cached", episode_id=episode.id)
            return existing

        primary = self._transcribe_primary(episode, audio_path)
        timestamped = self._transcribe_timestamps(episode, audio_path)
        merged = self._merge_transcripts(episode, primary, timestamped)

        return merged

    def _transcribe_primary(self, episode: Episode, audio_path: str) -> Transcript:
        """Transcribe with sofer.ai for accurate Hebrew text."""
        existing = (
            self.db.query(Transcript)
            .filter_by(episode_id=episode.id, transcript_type="primary")
            .first()
        )
        if existing:
            return existing

        import os
        api_key = os.environ.get("SOFER_AI_API_KEY", "")

        with open(audio_path, "rb") as f:
            resp = httpx.post(
                "https://api.sofer.ai/v1/transcribe",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (Path(audio_path).name, f)},
                data={"language": "he"},
                timeout=600,
            )
        resp.raise_for_status()
        result = resp.json()

        transcript = Transcript(
            episode_id=episode.id,
            transcript_type="primary",
            provider="sofer_ai",
            full_text=result.get("text", ""),
            language="he",
        )
        self.db.add(transcript)
        self.db.flush()
        logger.info("transcriber.primary_done", episode_id=episode.id)
        return transcript

    def _transcribe_timestamps(self, episode: Episode, audio_path: str) -> Transcript:
        """Transcribe with OpenAI Whisper for word-level timestamps."""
        existing = (
            self.db.query(Transcript)
            .filter_by(episode_id=episode.id, transcript_type="timestamped")
            .first()
        )
        if existing:
            return existing

        import os
        api_key = os.environ.get("OPENAI_API_KEY", "")

        with open(audio_path, "rb") as f:
            resp = httpx.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (Path(audio_path).name, f)},
                data={
                    "model": "whisper-1",
                    "language": "he",
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": "word",
                },
                timeout=600,
            )
        resp.raise_for_status()
        result = resp.json()

        words = [
            {"word": w["word"], "start_ms": int(w["start"] * 1000), "end_ms": int(w["end"] * 1000)}
            for w in result.get("words", [])
        ]

        transcript = Transcript(
            episode_id=episode.id,
            transcript_type="timestamped",
            provider="openai_whisper",
            full_text=result.get("text", ""),
            words=words,
            language="he",
        )
        self.db.add(transcript)
        self.db.flush()
        logger.info("transcriber.timestamps_done", episode_id=episode.id, word_count=len(words))
        return transcript

    def _merge_transcripts(
        self, episode: Episode, primary: Transcript, timestamped: Transcript
    ) -> Transcript:
        """Merge accurate sofer.ai text with Whisper timestamps via SequenceMatcher."""
        primary_words = (primary.full_text or "").split()
        whisper_words = timestamped.words or []

        whisper_texts = [w["word"] for w in whisper_words]
        matcher = SequenceMatcher(None, primary_words, whisper_texts)

        merged_words = []
        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            if op == "equal":
                for pi, wi in zip(range(i1, i2), range(j1, j2)):
                    merged_words.append({
                        "word": primary_words[pi],
                        "start_ms": whisper_words[wi]["start_ms"],
                        "end_ms": whisper_words[wi]["end_ms"],
                    })
            elif op == "replace":
                # Use sofer.ai text with whisper timestamps (interpolated)
                whisper_slice = whisper_words[j1:j2]
                start = whisper_slice[0]["start_ms"] if whisper_slice else 0
                end = whisper_slice[-1]["end_ms"] if whisper_slice else 0
                primary_slice = primary_words[i1:i2]
                n = len(primary_slice)
                for k, word in enumerate(primary_slice):
                    t_start = start + int((end - start) * k / max(n, 1))
                    t_end = start + int((end - start) * (k + 1) / max(n, 1))
                    merged_words.append({"word": word, "start_ms": t_start, "end_ms": t_end})
            elif op == "insert":
                # Words only in primary (no timestamps available) — interpolate
                if merged_words:
                    last_end = merged_words[-1]["end_ms"]
                else:
                    last_end = 0
                for word in primary_words[i1:i2]:
                    merged_words.append({"word": word, "start_ms": last_end, "end_ms": last_end})

        merged_text = " ".join(w["word"] for w in merged_words)

        transcript = Transcript(
            episode_id=episode.id,
            transcript_type="merged",
            provider="merged",
            full_text=merged_text,
            words=merged_words,
            language="he",
        )
        self.db.add(transcript)
        self.db.flush()
        logger.info(
            "transcriber.merged",
            episode_id=episode.id,
            word_count=len(merged_words),
        )
        return transcript
