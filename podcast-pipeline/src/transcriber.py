"""
transcriber.py — Transcribe audio using AssemblyAI, OpenAI Whisper, or Deepgram.

Returns a unified TranscriptResult regardless of which provider is used.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import get_secret
from .logger import get_logger

log = get_logger(__name__)


@dataclass
class ChapterTimestamp:
    """A chapter/section detected by the transcription provider."""
    title: str
    summary: str
    start_ms: int
    end_ms: int
    gist: str = ""


@dataclass
class TranscriptResult:
    text: str
    words: list[dict[str, Any]] = field(default_factory=list)
    utterances: list[dict[str, Any]] = field(default_factory=list)
    provider_chapters: list[ChapterTimestamp] = field(default_factory=list)
    language: str = "en"
    duration_seconds: float | None = None
    provider: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def word_at_time(self, time_ms: int) -> int:
        """Return approximate word index at a given timestamp."""
        for i, word in enumerate(self.words):
            if word.get("start", 0) >= time_ms:
                return i
        return len(self.words) - 1


# ---------------------------------------------------------------------------
# AssemblyAI
# ---------------------------------------------------------------------------

class AssemblyAITranscriber:
    BASE_URL = "https://api.assemblyai.com/v2"

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg["transcription"]["assemblyai"]
        self.api_key = get_secret("ASSEMBLYAI_API_KEY")
        self.headers = {
            "authorization": self.api_key,
            "content-type": "application/json",
        }

    def transcribe(self, audio_path: Path, output_dir: Path) -> TranscriptResult:
        import requests

        cache_path = output_dir / f"{audio_path.stem}_assemblyai.json"
        if cache_path.exists():
            log.info(f"Loading cached transcript: {cache_path}")
            return self._parse_response(json.loads(cache_path.read_text()))

        log.info("Uploading audio to AssemblyAI…")
        upload_url = self._upload(audio_path)

        log.info("Submitting transcription job…")
        transcript_id = self._submit(upload_url)

        log.info(f"Waiting for transcription (id={transcript_id})…")
        result = self._poll(transcript_id)

        cache_path.write_text(json.dumps(result, indent=2))
        log.info(f"Transcript saved: {cache_path}")

        return self._parse_response(result)

    def _upload(self, path: Path) -> str:
        import requests
        with path.open("rb") as f:
            resp = requests.post(
                f"{self.BASE_URL}/upload",
                headers={"authorization": self.api_key},
                data=f,
            )
        resp.raise_for_status()
        return resp.json()["upload_url"]

    def _submit(self, audio_url: str) -> str:
        import requests
        payload: dict[str, Any] = {
            "audio_url": audio_url,
            "speech_model": self.cfg.get("speech_model", "best"),
            "language_code": self.cfg.get("language_code", "en"),
            "auto_chapters": self.cfg.get("auto_chapters", True),
            "speaker_labels": self.cfg.get("speaker_labels", True),
        }
        if self.cfg.get("summarization"):
            payload["summarization"] = True
            payload["summary_model"] = self.cfg.get("summarization_model", "informative")
            payload["summary_type"] = "bullets_verbose"

        resp = requests.post(
            f"{self.BASE_URL}/transcript",
            json=payload,
            headers=self.headers,
        )
        resp.raise_for_status()
        return resp.json()["id"]

    def _poll(self, transcript_id: str, poll_interval: int = 5) -> dict:
        import requests
        url = f"{self.BASE_URL}/transcript/{transcript_id}"
        while True:
            resp = requests.get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            status = data["status"]
            if status == "completed":
                return data
            elif status == "error":
                raise RuntimeError(f"AssemblyAI transcription error: {data.get('error')}")
            log.debug(f"Transcription status: {status}, waiting {poll_interval}s…")
            time.sleep(poll_interval)

    def _parse_response(self, data: dict) -> TranscriptResult:
        chapters = []
        for ch in data.get("chapters") or []:
            chapters.append(ChapterTimestamp(
                title=ch.get("headline", ch.get("gist", "Chapter")),
                summary=ch.get("summary", ""),
                start_ms=ch.get("start", 0),
                end_ms=ch.get("end", 0),
                gist=ch.get("gist", ""),
            ))

        return TranscriptResult(
            text=data.get("text", ""),
            words=data.get("words") or [],
            utterances=data.get("utterances") or [],
            provider_chapters=chapters,
            language=data.get("language_code", "en"),
            duration_seconds=(data.get("audio_duration") or 0),
            provider="assemblyai",
            raw=data,
        )


# ---------------------------------------------------------------------------
# OpenAI Whisper
# ---------------------------------------------------------------------------

class OpenAIWhisperTranscriber:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg["transcription"]["openai_whisper"]
        self.api_key = get_secret("OPENAI_API_KEY")

    def transcribe(self, audio_path: Path, output_dir: Path) -> TranscriptResult:
        from openai import OpenAI

        cache_path = output_dir / f"{audio_path.stem}_whisper.json"
        if cache_path.exists():
            log.info(f"Loading cached transcript: {cache_path}")
            data = json.loads(cache_path.read_text())
            return TranscriptResult(text=data["text"], provider="openai_whisper", raw=data)

        client = OpenAI(api_key=self.api_key)
        chunk_minutes = self.cfg.get("chunk_minutes", 10)
        chunks = self._split_audio(audio_path, chunk_minutes)

        full_text_parts = []
        log.info(f"Transcribing {len(chunks)} audio chunk(s) with Whisper…")

        for i, chunk_path in enumerate(chunks):
            log.debug(f"Transcribing chunk {i + 1}/{len(chunks)}: {chunk_path}")
            with chunk_path.open("rb") as f:
                response = client.audio.transcriptions.create(
                    model=self.cfg.get("model", "whisper-1"),
                    file=f,
                    language=self.cfg.get("language", "en"),
                    response_format="verbose_json",
                    timestamp_granularities=["word"],
                )
            full_text_parts.append(response.text)

        full_text = " ".join(full_text_parts)
        result = {"text": full_text}
        cache_path.write_text(json.dumps(result, indent=2))

        return TranscriptResult(text=full_text, provider="openai_whisper", raw=result)

    def _split_audio(self, audio_path: Path, chunk_minutes: int) -> list[Path]:
        """Split audio into chunks using ffmpeg. Returns list of chunk paths."""
        import subprocess

        chunk_dir = audio_path.parent / f"{audio_path.stem}_chunks"
        chunk_dir.mkdir(exist_ok=True)

        chunk_pattern = str(chunk_dir / "chunk_%03d.mp3")
        chunk_seconds = chunk_minutes * 60

        cmd = [
            "ffmpeg", "-y", "-i", str(audio_path),
            "-f", "segment",
            "-segment_time", str(chunk_seconds),
            "-c", "copy",
            chunk_pattern,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg split failed: {result.stderr}")

        chunks = sorted(chunk_dir.glob("chunk_*.mp3"))
        return chunks


# ---------------------------------------------------------------------------
# Deepgram
# ---------------------------------------------------------------------------

class DeepgramTranscriber:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg["transcription"]["deepgram"]
        self.api_key = get_secret("DEEPGRAM_API_KEY")

    def transcribe(self, audio_path: Path, output_dir: Path) -> TranscriptResult:
        from deepgram import DeepgramClient, PrerecordedOptions

        cache_path = output_dir / f"{audio_path.stem}_deepgram.json"
        if cache_path.exists():
            log.info(f"Loading cached transcript: {cache_path}")
            data = json.loads(cache_path.read_text())
            return self._parse_response(data)

        client = DeepgramClient(self.api_key)
        log.info("Transcribing with Deepgram…")

        with audio_path.open("rb") as f:
            audio_data = f.read()

        options = PrerecordedOptions(
            model=self.cfg.get("model", "nova-2"),
            language=self.cfg.get("language", "en"),
            smart_format=self.cfg.get("smart_format", True),
            paragraphs=True,
            utterances=True,
            diarize=True,
        )

        response = client.listen.rest.v("1").transcribe_file(
            {"buffer": audio_data, "mimetype": "audio/mpeg"}, options
        )
        data = response.to_dict()
        cache_path.write_text(json.dumps(data, indent=2))

        return self._parse_response(data)

    def _parse_response(self, data: dict) -> TranscriptResult:
        results = data.get("results", {})
        channels = results.get("channels", [{}])
        alternatives = channels[0].get("alternatives", [{}])
        transcript = alternatives[0].get("transcript", "")
        words = alternatives[0].get("words", [])

        return TranscriptResult(
            text=transcript,
            words=words,
            provider="deepgram",
            raw=data,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_transcriber(cfg: dict):
    provider = cfg["transcription"]["provider"]
    log.info(f"Transcription provider: {provider}")

    if provider == "assemblyai":
        return AssemblyAITranscriber(cfg)
    elif provider == "openai_whisper":
        return OpenAIWhisperTranscriber(cfg)
    elif provider == "deepgram":
        return DeepgramTranscriber(cfg)
    else:
        raise ValueError(f"Unknown transcription provider: '{provider}'")
