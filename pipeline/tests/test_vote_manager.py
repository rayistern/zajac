"""Tests for vote manager — tallying, window expiry, approval logic."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from pipeline.config import ApprovalConfig, TelegramConfig
from pipeline.db import VoteSession
from pipeline.vote_manager import VoteManager


@pytest.fixture
def approval_config():
    return ApprovalConfig(min_approval_percentage=70, min_total_votes=3)


@pytest.fixture
def telegram_config():
    return TelegramConfig(voting_window_hours=24)


@pytest.fixture
def manager(approval_config, telegram_config):
    session = MagicMock()
    return VoteManager(approval_config, telegram_config, session)


class TestRecordVote:
    def test_rejects_vote_on_closed_session(self, manager):
        session = MagicMock(status="closed")
        manager.db.query().get.return_value = session

        result = manager.record_vote(
            vote_session_id=1, telegram_user_id=100, telegram_username="u", vote_type="upvote"
        )
        assert result is None

    def test_returns_none_for_missing_session(self, manager):
        manager.db.query().get.return_value = None

        result = manager.record_vote(
            vote_session_id=999, telegram_user_id=100, telegram_username="u", vote_type="upvote"
        )
        assert result is None


class TestCloseSessionApproval:
    def test_approves_when_threshold_met(self, manager):
        """7 up / 3 down = 70% with 10 votes → meets both thresholds."""
        session = VoteSession(
            id=1, artifact_version_id=1, upvotes_count=7, downvotes_count=3,
            voting_opened_at=datetime.utcnow(), voting_window_hours=1,
            status="open",
        )
        manager._update_artifact_status = MagicMock()

        manager._close_session(session)

        assert session.status == "approved"
        assert session.approval_percentage == 70.0
        assert session.approved_at is not None
        manager._update_artifact_status.assert_called_once_with(session, "approved")

    def test_rejects_below_approval_percentage(self, manager):
        """5 up / 5 down = 50%, below 70% threshold."""
        session = VoteSession(
            id=1, artifact_version_id=1, upvotes_count=5, downvotes_count=5,
            voting_opened_at=datetime.utcnow(), voting_window_hours=1,
        )
        manager._update_artifact_status = MagicMock()

        manager._close_session(session)

        assert session.status == "rejected"
        assert session.approval_percentage == 50.0
        manager._update_artifact_status.assert_called_once_with(session, "rejected")

    def test_rejects_below_min_total_votes(self, manager):
        """2 up / 0 down = 100%, but only 2 votes < min 3."""
        session = VoteSession(
            id=1, artifact_version_id=1, upvotes_count=2, downvotes_count=0,
            voting_opened_at=datetime.utcnow(), voting_window_hours=1,
        )
        manager._update_artifact_status = MagicMock()

        manager._close_session(session)

        assert session.status == "rejected"
        manager._update_artifact_status.assert_called_once_with(session, "rejected")

    def test_rejects_zero_votes(self, manager):
        session = VoteSession(
            id=1, artifact_version_id=1, upvotes_count=0, downvotes_count=0,
            voting_opened_at=datetime.utcnow(), voting_window_hours=1,
        )
        manager._update_artifact_status = MagicMock()

        manager._close_session(session)

        assert session.status == "rejected"
        assert session.approval_percentage == 0

    def test_sets_voting_closed_at(self, manager):
        session = VoteSession(
            id=1, artifact_version_id=1, upvotes_count=5, downvotes_count=0,
            voting_opened_at=datetime.utcnow(), voting_window_hours=1,
        )
        manager._update_artifact_status = MagicMock()

        before = datetime.utcnow()
        manager._close_session(session)
        after = datetime.utcnow()

        assert before <= session.voting_closed_at <= after
