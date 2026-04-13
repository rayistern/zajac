"""
pipeline.py — Orchestrates the full end-to-end podcast processing pipeline.

Flow per episode:
  1. Parse RSS feed → find new episodes
  2. Download audio
  3. Transcribe audio → full transcript + optional provider chapters
  4. Split transcript into chapters (provider timestamps or LLM)
  5. For each chapter:
     a. Generate an image prompt via LLM
     b. Generate the image
  6. Post chapter images + captions to Telegram
  7. Mark episode as done in state DB
"""

from __future__ import annotations

import concurrent.futures
import traceback
from pathlib import Path

from .chapter_splitter import Chapter, ChapterSplitter
from .config import load_config
from .downloader import Downloader
from .image_generator import ImageGenerator
from .image_prompt_generator import ImagePromptGenerator
from .logger import get_logger, setup_logger
from .rss_parser import Episode, RSSParser
from .state import StateDB
from .telegram_poster import TelegramPoster
from .transcriber import TranscriptResult, get_transcriber

log = get_logger(__name__)


class Pipeline:
    def __init__(self, config_path: str = "config.yaml") -> None:
        self.cfg = load_config(config_path)
        pl_cfg = self.cfg["pipeline"]

        setup_logger(
            level=pl_cfg.get("log_level", "INFO"),
            log_file=pl_cfg.get("log_file"),
        )

        self.state = StateDB(pl_cfg.get("state_db", "./pipeline_state.db"))
        self.rss = RSSParser(self.cfg)
        self.downloader = Downloader(self.cfg)
        self.transcriber = get_transcriber(self.cfg)
        self.chapter_splitter = ChapterSplitter(self.cfg)
        self.prompt_gen = ImagePromptGenerator(self.cfg)
        self.image_gen = ImageGenerator(self.cfg)
        self.telegram = TelegramPoster(self.cfg)

        self.transcript_dir = Path(self.cfg["transcription"]["output_dir"])
        self.transcript_dir.mkdir(parents=True, exist_ok=True)

        self.cleanup_audio = pl_cfg.get("cleanup_audio", False)
        self.cleanup_transcripts = pl_cfg.get("cleanup_transcripts", False)
        self.image_concurrency = pl_cfg.get("image_concurrency", 2)
        self.force_reprocess = self.cfg["rss"].get("force_reprocess", False)

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def run(self, feed_url: str | None = None) -> None:
        """Fetch the RSS feed and process new episodes."""
        episodes = self.rss.fetch_episodes(feed_url)
        if not episodes:
            log.info("No episodes to process.")
            return

        for episode in episodes:
            self._process_episode(episode)

    def run_episode(self, episode: Episode) -> None:
        """Process a single episode directly (useful for testing)."""
        self._process_episode(episode)

    # ------------------------------------------------------------------
    # Episode processing
    # ------------------------------------------------------------------

    def _process_episode(self, episode: Episode) -> None:
        log.info(f"{'='*60}")
        log.info(f"Processing episode: {episode.title}")
        log.info(f"{'='*60}")

        if not self.force_reprocess and self.state.is_episode_processed(episode.guid):
            log.info(f"Already processed, skipping: {episode.title}")
            return

        self.state.upsert_episode(
            episode.guid,
            feed_url=episode.feed_url,
            title=episode.title,
            published_at=episode.published_at.isoformat() if episode.published_at else None,
            audio_url=episode.audio_url,
            status="processing",
        )

        try:
            # Step 1: Download
            audio_path = self.downloader.download(episode.audio_url, episode.guid)
            self.state.upsert_episode(episode.guid, local_audio=str(audio_path))

            # Step 2: Transcribe
            transcript = self.transcriber.transcribe(audio_path, self.transcript_dir)
            self.state.upsert_episode(
                episode.guid,
                transcript_path=str(self.transcript_dir / f"{audio_path.stem}.json"),
            )

            # Step 3: Split into chapters
            chapters = self.chapter_splitter.split(
                transcript,
                episode_title=episode.title,
                podcast_title=episode.show_title,
            )
            log.info(f"Episode split into {len(chapters)} chapter(s).")

            # Step 4: Generate prompts + images (with concurrency)
            images = self._generate_images_concurrent(chapters, episode)

            # Step 5: Post to Telegram
            send_mode = self.cfg["telegram"]["send_mode"]
            if send_mode == "episode_summary":
                self.telegram.post_episode_summary(chapters, images, episode)
            else:
                for chapter, image_path in zip(chapters, images):
                    msg_id = self.telegram.post_chapter(
                        chapter, image_path, episode, len(chapters)
                    )
                    self.state.save_chapter(
                        episode.guid,
                        chapter.number,
                        title=chapter.title,
                        summary=chapter.summary,
                        image_path=str(image_path) if image_path else None,
                        telegram_msg_id=msg_id,
                        status="done",
                    )

            # Step 6: Cleanup & mark done
            if self.cleanup_audio and audio_path.exists():
                audio_path.unlink()
                log.debug(f"Deleted audio: {audio_path}")

            self.state.mark_episode_done(episode.guid)
            log.info(f"✅ Episode complete: {episode.title}")

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            log.error(f"Episode failed: {error_msg}")
            log.debug(traceback.format_exc())
            self.state.mark_episode_error(episode.guid, error_msg)

    # ------------------------------------------------------------------
    # Concurrent image generation
    # ------------------------------------------------------------------

    def _generate_images_concurrent(
        self, chapters: list[Chapter], episode: Episode
    ) -> list[Path | None]:
        results: list[Path | None] = [None] * len(chapters)

        def process_chapter(args: tuple[int, Chapter]) -> tuple[int, Path | None]:
            idx, chapter = args
            try:
                prompt = self.prompt_gen.generate(
                    chapter,
                    episode_title=episode.title,
                    podcast_title=episode.show_title,
                    total_chapters=len(chapters),
                )
                self.state.save_chapter(
                    episode.guid, chapter.number,
                    title=chapter.title,
                    summary=chapter.summary,
                    image_prompt=prompt,
                    status="generating_image",
                )

                stem = f"{episode.guid[:8]}_ch{chapter.number:02d}"
                image_path = self.image_gen.generate(prompt, stem)

                self.state.save_chapter(
                    episode.guid, chapter.number,
                    image_path=str(image_path),
                    status="image_done",
                )
                return idx, image_path
            except Exception as exc:
                log.error(f"Failed to generate image for chapter {chapter.number}: {exc}")
                self.state.save_chapter(
                    episode.guid, chapter.number,
                    status="image_error",
                    error=str(exc),
                )
                return idx, None

        max_workers = min(self.image_concurrency, len(chapters))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_chapter, (i, ch)): i
                for i, ch in enumerate(chapters)
            }
            for future in concurrent.futures.as_completed(futures):
                idx, image_path = future.result()
                results[idx] = image_path

        return results
