"""Main pipeline entry point."""

import structlog

logger = structlog.get_logger()


def main():
    logger.info("pipeline.start", message="Merkos Rambam pipeline starting")
    # TODO: Implement pipeline orchestration
    # 1. RSS ingestion
    # 2. Dual transcription
    # 3. Sefaria text fetch
    # 4. 4-pass LLM alignment
    # 5. Artifact planning
    # 6. Image generation
    # 7. Telegram voting
    # 8. WhatsApp distribution
    logger.info("pipeline.done", message="Pipeline run complete")


if __name__ == "__main__":
    main()
