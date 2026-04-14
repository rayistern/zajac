"""Dual transcription: sofer.ai (accuracy) + Whisper (timestamps) → merge."""

from __future__ import annotations

import os
import subprocess
from difflib import SequenceMatcher
from pathlib import Path

import httpx
import structlog
from sqlalchemy.orm import Session

from .config import TranscriptionConfig
from .db import Episode, Transcript

logger = structlog.get_logger()


def _probe_audio_duration_ms(audio_path: str) -> int | None:
    """Probe audio duration in milliseconds via ffprobe, returning None on failure."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(float(result.stdout.strip()) * 1000)
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        pass
    return None


class DualTranscriber:
    def __init__(self, config: TranscriptionConfig, session: Session):
        self.config = config
        self.db = session

    def transcribe(self, episode: Episode, audio_path: str) -> Transcript:
        """Run dual transcription and merge results.

        If config.timestamp_provider is 'synthetic' or OPENAI_API_KEY is not set,
        skips Whisper and produces synthetic word-level timestamps by distributing
        words proportionally across the audio duration.
        """
        existing = (
            self.db.query(Transcript)
            .filter_by(episode_id=episode.id, transcript_type="merged")
            .first()
        )
        if existing:
            logger.info("transcriber.cached", episode_id=episode.id)
            return existing

        primary = self._transcribe_primary(episode, audio_path)

        use_whisper = (
            self.config.timestamp_provider == "openai_whisper"
            and os.environ.get("OPENAI_API_KEY")
        )

        if use_whisper:
            timestamped = self._transcribe_timestamps(episode, audio_path)
            merged = self._merge_transcripts(episode, primary, timestamped)
        else:
            merged = self._synthetic_merge(episode, primary, audio_path)

        return merged

    def _synthetic_merge(
        self, episode: Episode, primary: Transcript, audio_path: str
    ) -> Transcript:
        """Build a merged transcript using sofer.ai text + synthetic per-word timestamps.

        Timestamps are computed by distributing primary words uniformly across
        the audio duration. This is a best-effort fallback when Whisper isn't
        available; accurate enough for text alignment to source units.
        """
        words = (primary.full_text or "").split()
        duration_ms = _probe_audio_duration_ms(audio_path) or max(len(words) * 400, 1)

        merged_words = []
        n = len(words)
        for i, w in enumerate(words):
            start = int(duration_ms * i / max(n, 1))
            end = int(duration_ms * (i + 1) / max(n, 1))
            merged_words.append({"word": w, "start_ms": start, "end_ms": end})

        transcript = Transcript(
            episode_id=episode.id,
            transcript_type="merged",
            provider="sofer_ai+synthetic",
            full_text=primary.full_text or "",
            words=merged_words,
            language="he",
        )
        self.db.add(transcript)
        self.db.flush()
        logger.info(
            "transcriber.synthetic_merged",
            episode_id=episode.id,
            word_count=n,
            duration_ms=duration_ms,
        )
        return transcript

    def _transcribe_primary(self, episode: Episode, audio_path: str) -> Transcript:
        """Transcribe with sofer.ai for accurate Hebrew text."""
        existing = (
            self.db.query(Transcript)
            .filter_by(episode_id=episode.id, transcript_type="primary")
            .first()
        )
        if existing:
            return existing

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
            elif op == "delete":
                # Words in primary but not in whisper — interpolate from
                # last known timestamp. SequenceMatcher semantics: 'delete'
                # means a[i1:i2] has items, b[j1:j2] is empty.
                if merged_words:
                    last_end = merged_words[-1]["end_ms"]
                else:
                    last_end = 0
                for word in primary_words[i1:i2]:
                    merged_words.append({"word": word, "start_ms": last_end, "end_ms": last_end})
            elif op == "insert":
                # Whisper has words primary doesn't. Primary is source of
                # truth for text, so drop these.
                pass

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
