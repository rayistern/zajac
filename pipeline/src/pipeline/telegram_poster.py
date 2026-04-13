"""Post generated artifacts to Telegram voting group for editorial review."""

from __future__ import annotations

import structlog
from sqlalchemy.orm import Session
from telegram import Bot

from .config import TelegramConfig
from .db import Artifact, ArtifactVersion, SourceUnit, VoteSession

logger = structlog.get_logger()


class TelegramPoster:
    def __init__(self, config: TelegramConfig, session: Session):
        self.config = config
        self.db = session
        self.bot = Bot(token=config.bot_token)

    async def post_for_review(
        self,
        artifact: Artifact,
        version: ArtifactVersion,
        source_unit: SourceUnit,
    ) -> VoteSession:
        """Post an artifact version to the voting group and open a vote session."""
        caption = (
            f"📖 {source_unit.sefaria_ref}\n"
            f"🎨 {artifact.subtype} | Style: {version.style_name}\n"
            f"Priority: {artifact.priority} | Position: {artifact.position:.1f}\n\n"
            f"Vote: {self.config.upvote_emoji} approve / {self.config.downvote_emoji} reject\n"
            f"Reply to request edits or style changes."
        )

        if version.url:
            message = await self.bot.send_photo(
                chat_id=self.config.voting_group_chat_id,
                photo=version.url,
                caption=caption,
            )
        else:
            message = await self.bot.send_message(
                chat_id=self.config.voting_group_chat_id,
                text=f"[No image URL]\n{caption}",
            )

        vote_session = VoteSession(
            artifact_version_id=version.id,
            telegram_message_id=message.message_id,
            telegram_chat_id=int(self.config.voting_group_chat_id),
            voting_window_hours=self.config.voting_window_hours,
            status="open",
        )
        self.db.add(vote_session)
        self.db.flush()

        version.vote_session_id = vote_session.id
        version.status = "in_review"
        artifact.status = "in_review"
        self.db.flush()

        logger.info(
            "telegram.posted",
            artifact_id=artifact.id,
            version_id=version.id,
            message_id=message.message_id,
        )
        return vote_session

    async def send_approval_notification(self, vote_session: VoteSession) -> None:
        """Notify the group that an artifact was approved."""
        await self.bot.send_message(
            chat_id=vote_session.telegram_chat_id,
            reply_to_message_id=vote_session.telegram_message_id,
            text=f"✅ Approved ({vote_session.approval_percentage:.0f}% with "
            f"{vote_session.upvotes_count + vote_session.downvotes_count} votes)",
        )

    async def send_rejection_notification(self, vote_session: VoteSession) -> None:
        """Notify the group that an artifact was rejected."""
        await self.bot.send_message(
            chat_id=vote_session.telegram_chat_id,
            reply_to_message_id=vote_session.telegram_message_id,
            text=f"❌ Rejected ({vote_session.approval_percentage:.0f}% approval, "
            f"needed {70}%)",
        )
