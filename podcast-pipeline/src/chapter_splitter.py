"""
chapter_splitter.py — Split a transcript into chapters.

Strategy "provider"  — use timestamps from the transcription provider.
Strategy "llm"       — ask an LLM to identify logical chapter breaks.
Strategy "both"      — prefer provider chapters; fall back to LLM if none found.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .config import get_secret, load_prompts, format_prompt
from .logger import get_logger
from .transcriber import TranscriptResult

log = get_logger(__name__)


@dataclass
class Chapter:
    number: int
    title: str
    summary: str
    text: str
    start_ms: int | None = None
    end_ms: int | None = None
    word_start: int | None = None
    word_end: int | None = None

    @property
    def excerpt(self, max_words: int = 80) -> str:
        words = self.text.split()
        return " ".join(words[:max_words]) + ("…" if len(words) > max_words else "")


class ChapterSplitter:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.ch_cfg = cfg["chapters"]
        self.prompts = load_prompts()

    def split(
        self,
        transcript: TranscriptResult,
        episode_title: str,
        podcast_title: str,
    ) -> list[Chapter]:
        strategy = self.ch_cfg["strategy"]

        provider_chapters = self._from_provider(transcript)
        if strategy == "provider":
            if provider_chapters:
                return provider_chapters
            log.warning("No provider chapters found, falling back to LLM.")

        if strategy == "llm" or (strategy == "both" and not provider_chapters):
            return self._from_llm(transcript, episode_title, podcast_title)

        if strategy == "both" and provider_chapters:
            return provider_chapters

        raise ValueError(f"Unknown chapter strategy: '{strategy}'")

    # ------------------------------------------------------------------
    # Provider chapters
    # ------------------------------------------------------------------

    def _from_provider(self, transcript: TranscriptResult) -> list[Chapter]:
        if not transcript.provider_chapters:
            return []

        log.info(f"Using {len(transcript.provider_chapters)} provider-detected chapter(s).")
        chapters = []
        all_words = transcript.words
        full_text = transcript.text

        for i, pc in enumerate(transcript.provider_chapters):
            # Extract text between timestamps using word-level data if available
            if all_words:
                segment_words = [
                    w["text"] for w in all_words
                    if pc.start_ms <= w.get("start", 0) <= pc.end_ms
                ]
                text = " ".join(segment_words)
            else:
                # Fall back to character-level slicing (less precise)
                start_char = int((pc.start_ms / 1000) / (transcript.duration_seconds or 1)
                                 * len(full_text))
                end_char = int((pc.end_ms / 1000) / (transcript.duration_seconds or 1)
                               * len(full_text))
                text = full_text[start_char:end_char]

            chapters.append(Chapter(
                number=i + 1,
                title=pc.title,
                summary=pc.summary,
                text=text,
                start_ms=pc.start_ms,
                end_ms=pc.end_ms,
            ))

        return chapters

    # ------------------------------------------------------------------
    # LLM chapters
    # ------------------------------------------------------------------

    def _from_llm(
        self,
        transcript: TranscriptResult,
        episode_title: str,
        podcast_title: str,
    ) -> list[Chapter]:
        llm_cfg = self.ch_cfg["llm"]
        max_chapters = llm_cfg.get("max_chapters", 10)
        min_words = llm_cfg.get("min_words_per_chapter", 200)

        log.info(f"Asking LLM to split transcript into chapters (max={max_chapters})…")

        prompt_tmpl = self.prompts["chapter_split"]
        words = transcript.text.split()

        user_prompt = format_prompt(
            prompt_tmpl["user"],
            podcast_title=podcast_title,
            episode_title=episode_title,
            chapter_text=transcript.text,
            max_chapters=max_chapters,
            min_words=min_words,
        )
        system_prompt = prompt_tmpl["system"]

        raw_json = self._call_llm(llm_cfg, system_prompt, user_prompt)

        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            # Try stripping markdown code fences
            cleaned = raw_json.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(cleaned)

        chapters = []
        for i, ch_data in enumerate(data["chapters"]):
            start_w = ch_data["start_word_index"]
            end_w = ch_data["end_word_index"]
            chapter_words = words[start_w: end_w + 1]
            chapters.append(Chapter(
                number=i + 1,
                title=ch_data["title"],
                summary=ch_data["summary"],
                text=" ".join(chapter_words),
                word_start=start_w,
                word_end=end_w,
            ))

        log.info(f"LLM generated {len(chapters)} chapter(s).")
        return chapters

    def _call_llm(self, llm_cfg: dict, system: str, user: str) -> str:
        provider = llm_cfg.get("provider", "anthropic")
        model = llm_cfg.get("model", "claude-opus-4-6")

        if provider == "anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text

        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=get_secret("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content

        elif provider == "google":
            import google.generativeai as genai
            genai.configure(api_key=get_secret("GOOGLE_API_KEY"))
            model_obj = genai.GenerativeModel(model, system_instruction=system)
            response = model_obj.generate_content(user)
            return response.text

        else:
            raise ValueError(f"Unknown LLM provider: '{provider}'")
