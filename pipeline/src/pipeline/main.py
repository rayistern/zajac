"""Main pipeline orchestrator — wires all stages together."""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime
from pathlib import Path

import structlog

from .config import load_config
from .db import (
    Artifact,
    Class,
    Episode,
    PipelineRun,
    SourceUnit,
    get_session_factory,
)

logger = structlog.get_logger()


def configure_logging(log_level: str = "INFO", log_format: str = "json"):
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def run_pipeline(
    class_ids: list[int] | None = None,
    episode_ids: list[int] | None = None,
    stages: list[str] | None = None,
    config_path: str | None = None,
):
    """Run the full or partial pipeline."""
    config = load_config(config_path)
    configure_logging(config.pipeline.log_level, config.pipeline.log_format)

    correlation_id = str(uuid.uuid4())[:8]
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

    logger.info("pipeline.start", correlation_id=correlation_id)

    if not config.database_url:
        logger.error("pipeline.no_database_url")
        sys.exit(1)

    SessionFactory = get_session_factory(config.database_url)
    session = SessionFactory()

    # Create pipeline run record
    run = PipelineRun(
        run_type="full" if not stages else "partial",
        requested_scope={
            "class_ids": class_ids,
            "episode_ids": episode_ids,
            "stages": stages or ["all"],
        },
        model_versions={
            "alignment": config.text_alignment.llm.model,
            "planning": config.artifact_planning.llm.model,
            "image": config.image_generation.replicate.model,
        },
        stages_status={},
        triggered_by="cli",
    )
    session.add(run)
    session.flush()

    all_stages = stages or [
        "transcription",
        "sefaria",
        "alignment",
        "planning",
        "generation",
        "telegram",
    ]

    try:
        # Get episodes to process
        episodes = _get_episodes(session, class_ids, episode_ids)
        if not episodes:
            logger.warning("pipeline.no_episodes")
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            session.commit()
            return

        for episode in episodes:
            _process_episode(session, config, run, episode, all_stages)

        # Close expired vote sessions
        if "telegram" in all_stages:
            from .vote_manager import VoteManager
            vm = VoteManager(config.approval, config.telegram, session)
            closed = vm.close_expired_sessions()
            run.stages_status["vote_tally"] = f"closed {len(closed)} sessions"

        run.status = "completed"
        run.completed_at = datetime.utcnow()
        session.commit()
        logger.info("pipeline.done", run_id=run.id)

    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = datetime.utcnow()
        session.commit()
        logger.error("pipeline.failed", error=str(e))
        raise


def _get_episodes(session, class_ids, episode_ids) -> list[Episode]:
    query = session.query(Episode)
    if episode_ids:
        query = query.filter(Episode.id.in_(episode_ids))
    elif class_ids:
        query = query.filter(Episode.class_id.in_(class_ids))
    else:
        query = query.filter_by(status="pending")
    return query.all()


def _process_episode(session, config, run, episode, stages):
    """Process a single episode through all requested stages."""
    log = logger.bind(episode_id=episode.id)
    log.info("episode.start")

    klass = session.query(Class).get(episode.class_id)
    episode.status = "processing"
    session.flush()

    try:
        transcript = None
        source_units = []
        alignments = []

        # Stage 1: Transcription
        if "transcription" in stages and episode.local_audio_path:
            from .dual_transcriber import DualTranscriber
            transcriber = DualTranscriber(config.transcription, session)
            transcript = transcriber.transcribe(episode, episode.local_audio_path)
            run.stages_status["transcription"] = "done"
            session.flush()

        # Stage 2: Sefaria text fetch
        if "sefaria" in stages and klass and klass.work_id:
            from .sefaria_client import SefariaClient
            sefaria = SefariaClient(config.sefaria, session)
            work = session.query(SourceUnit).filter_by(work_id=klass.work_id).first()
            if klass.current_level_1 and klass.current_level_2:
                from .db import Work
                work_obj = session.query(Work).get(klass.work_id)
                if work_obj:
                    source_units = sefaria.fetch_perek(
                        work_obj, klass.current_level_1, klass.current_level_2
                    )
            sefaria.close()
            run.stages_status["sefaria"] = "done"
            session.flush()

        # Stage 3: Alignment
        if "alignment" in stages and transcript and source_units:
            from .text_aligner import TextAligner
            aligner = TextAligner(config.text_alignment, session)
            alignments = aligner.align(transcript, source_units)
            run.stages_status["alignment"] = "done"
            session.flush()

        # Stage 4: Artifact planning + generation
        if "planning" in stages and source_units:
            from .artifact_planner import ArtifactPlanner
            from .context_synthesizer import ContextSynthesizer

            synthesizer = ContextSynthesizer(
                config.artifact_planning.llm.model, session
            )
            planner = ArtifactPlanner(config.artifact_planning, session)

            for su in source_units:
                context = synthesizer.get_context(
                    su,
                    transcript=transcript,
                    alignments=alignments,
                    mode=config.artifact_planning.context_mode,
                    class_id=klass.id if klass else None,
                )

                existing = (
                    session.query(Artifact)
                    .filter_by(source_unit_id=su.id)
                    .all()
                )

                plan = planner.plan(
                    su,
                    context,
                    class_id=klass.id if klass else None,
                    existing_artifacts=existing,
                )

                artifacts = planner.create_artifacts_from_plan(
                    plan, su,
                    class_id=klass.id if klass else None,
                    pipeline_run_id=run.id,
                )

                # Stage 5: Image generation
                if "generation" in stages:
                    from .image_generator import ImageGenerator
                    generator = ImageGenerator(config.image_generation, session)

                    for artifact in artifacts:
                        plan_item = next(
                            (
                                item
                                for item in (plan.plan_items or [])
                                if item.get("priority") == artifact.priority
                            ),
                            {},
                        )
                        version = generator.generate(
                            artifact,
                            context=context,
                            prompt_focus=plan_item.get("prompt_focus", ""),
                            pipeline_run_id=run.id,
                        )

                        # Stage 6: Post to Telegram
                        if "telegram" in stages and config.telegram.bot_token:
                            from .telegram_poster import TelegramPoster
                            poster = TelegramPoster(config.telegram, session)
                            asyncio.run(poster.post_for_review(artifact, version, su))

            run.stages_status["planning"] = "done"
            run.stages_status["generation"] = "done"
            session.flush()

        episode.status = "done"
        episode.processed_at = datetime.utcnow()
        session.flush()
        log.info("episode.done")

    except Exception as e:
        episode.status = "error"
        episode.error_message = str(e)
        session.flush()
        log.error("episode.failed", error=str(e))
        raise


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Merkos Rambam content pipeline")
    parser.add_argument("--class-ids", type=int, nargs="*", help="Process specific class IDs")
    parser.add_argument("--episode-ids", type=int, nargs="*", help="Process specific episode IDs")
    parser.add_argument(
        "--stages",
        nargs="*",
        choices=["transcription", "sefaria", "alignment", "planning", "generation", "telegram"],
        help="Run specific stages only",
    )
    parser.add_argument("--config", type=str, help="Path to config.yaml")

    args = parser.parse_args()
    run_pipeline(
        class_ids=args.class_ids,
        episode_ids=args.episode_ids,
        stages=args.stages,
        config_path=args.config,
    )


if __name__ == "__main__":
    main()
