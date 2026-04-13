"""Tally votes from Telegram reactions, approve/reject based on thresholds."""

from __future__ import annotations

from datetime import datetime, timedelta

import structlog
from sqlalchemy.orm import Session

from .config import ApprovalConfig, TelegramConfig
from .db import Artifact, ArtifactVersion, Vote, VoteSession

logger = structlog.get_logger()


class VoteManager:
    def __init__(
        self,
        approval_config: ApprovalConfig,
        telegram_config: TelegramConfig,
        session: Session,
    ):
        self.approval = approval_config
        self.telegram = telegram_config
        self.db = session

    def record_vote(
        self,
        vote_session_id: int,
        telegram_user_id: int,
        telegram_username: str | None,
        vote_type: str,
    ) -> Vote | None:
        """Record a vote, updating tallies. Returns None if session is closed."""
        session = self.db.query(VoteSession).get(vote_session_id)
        if not session or session.status != "open":
            return None

        # Upsert vote
        existing = (
            self.db.query(Vote)
            .filter_by(vote_session_id=vote_session_id, telegram_user_id=telegram_user_id)
            .first()
        )

        if existing:
            old_type = existing.vote_type
            existing.vote_type = vote_type
            existing.voted_at = datetime.utcnow()
            if old_type != vote_type:
                if old_type == "upvote":
                    session.upvotes_count = max(0, (session.upvotes_count or 0) - 1)
                else:
                    session.downvotes_count = max(0, (session.downvotes_count or 0) - 1)
                if vote_type == "upvote":
                    session.upvotes_count = (session.upvotes_count or 0) + 1
                else:
                    session.downvotes_count = (session.downvotes_count or 0) + 1
            vote = existing
        else:
            vote = Vote(
                vote_session_id=vote_session_id,
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_username,
                vote_type=vote_type,
            )
            self.db.add(vote)
            if vote_type == "upvote":
                session.upvotes_count = (session.upvotes_count or 0) + 1
            else:
                session.downvotes_count = (session.downvotes_count or 0) + 1

        total = (session.upvotes_count or 0) + (session.downvotes_count or 0)
        if total > 0:
            session.approval_percentage = (session.upvotes_count or 0) / total * 100

        self.db.flush()
        logger.info(
            "votes.recorded",
            session_id=vote_session_id,
            user_id=telegram_user_id,
            vote=vote_type,
            total=total,
        )
        return vote

    def close_expired_sessions(self) -> list[VoteSession]:
        """Close all vote sessions past their voting window."""
        now = datetime.utcnow()
        open_sessions = (
            self.db.query(VoteSession)
            .filter_by(status="open")
            .all()
        )

        closed = []
        for session in open_sessions:
            window = timedelta(hours=session.voting_window_hours or self.telegram.voting_window_hours)
            if session.voting_opened_at and now >= session.voting_opened_at + window:
                self._close_session(session)
                closed.append(session)

        self.db.flush()
        logger.info("votes.closed_expired", count=len(closed))
        return closed

    def _close_session(self, session: VoteSession) -> None:
        """Close a voting session and determine approval/rejection."""
        session.voting_closed_at = datetime.utcnow()
        total = (session.upvotes_count or 0) + (session.downvotes_count or 0)

        if total > 0:
            session.approval_percentage = (session.upvotes_count or 0) / total * 100
        else:
            session.approval_percentage = 0

        approved = (
            total >= self.approval.min_total_votes
            and (session.approval_percentage or 0) >= self.approval.min_approval_percentage
        )

        if approved:
            session.status = "approved"
            session.approved_at = datetime.utcnow()
            self._update_artifact_status(session, "approved")
        else:
            session.status = "rejected"
            self._update_artifact_status(session, "rejected")

        logger.info(
            "votes.session_closed",
            session_id=session.id,
            status=session.status,
            approval=session.approval_percentage,
            total_votes=total,
        )

    def _update_artifact_status(self, session: VoteSession, status: str) -> None:
        version = self.db.query(ArtifactVersion).get(session.artifact_version_id)
        if version:
            version.status = status
            artifact = self.db.query(Artifact).get(version.artifact_id)
            if artifact:
                artifact.status = status
