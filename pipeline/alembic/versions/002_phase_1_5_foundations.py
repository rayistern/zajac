"""Phase 1.5 foundations: chatbot_sessions + quiz artifact subtype.

Revision ID: 002
Revises: 001
Create Date: 2026-04-15

Adds pipeline-side tables for the Phase 1.5 raise-hand chatbot (#15)
and documents the new ``quiz`` artifact subtype (#16).

Notes:
- ``artifact.subtype`` is plain ``sa.Text`` (see migration 001), not an
  enum. No schema change is required to admit ``quiz`` as a value — the
  publisher maps it to the web-read ``content_type`` via
  ``pipeline.publisher.SUBTYPE_TO_CONTENT_TYPE``. We add a named CHECK
  constraint here so misspelled subtypes fail fast at write time rather
  than producing silently-dropped content rows downstream.
- ``chatbot_sessions`` is the audit trail for raise-hand queries. All
  LLM spend flows through Vercel AI Gateway and cost is recorded per
  row via ``providerMetadata.gateway.cost`` at onFinish time.
- ``chatbot_messages`` stores structured message parts (Vercel AI SDK
  ``Message_v2.parts`` shape) so we can replay conversations without
  re-running the model.
- ``device_spend`` is the monthly USD backstop that pairs with the
  per-device daily request counter enforced at the API layer.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


# Canonical allow-list for artifact.subtype. Keep in sync with
# pipeline/src/pipeline/publisher.py::SUBTYPE_TO_CONTENT_TYPE.
ARTIFACT_SUBTYPES = (
    "illustration",
    "diagram",
    "infographic",
    "chart",
    "timeline",
    "map",
    "quiz",
)


def upgrade() -> None:
    op.create_table(
        "chatbot_sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("device_id", sa.Text, nullable=False),
        sa.Column(
            "source_unit_id",
            sa.Integer,
            sa.ForeignKey("source_units.id"),
        ),
        sa.Column("episode_id", sa.Integer, sa.ForeignKey("episodes.id")),
        sa.Column("playback_ms", sa.Integer),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("response_text", sa.Text),
        sa.Column("llm_model", sa.Text),
        sa.Column("context_tokens_in", sa.Integer),
        sa.Column("context_tokens_out", sa.Integer),
        sa.Column("cost_usd", sa.Numeric(10, 6)),
        sa.Column("latency_ms", sa.Integer),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_chatbot_sessions_device_created",
        "chatbot_sessions",
        ["device_id", "created_at"],
    )

    op.create_table(
        "chatbot_messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "session_id",
            sa.Integer,
            sa.ForeignKey("chatbot_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("parts", JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_chatbot_messages_session",
        "chatbot_messages",
        ["session_id"],
    )

    op.create_table(
        "device_spend",
        sa.Column("device_id", sa.Text, nullable=False),
        sa.Column("month", sa.Text, nullable=False),  # YYYY-MM
        sa.Column(
            "usd_spent",
            sa.Numeric(10, 6),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("device_id", "month"),
    )

    # Constrain artifact.subtype to the allow-list so new features that
    # add a subtype must touch this migration + publisher mapping in
    # lockstep. ``quiz`` joins the existing image subtypes here.
    allowed = ", ".join(f"'{s}'" for s in ARTIFACT_SUBTYPES)
    op.create_check_constraint(
        "ck_artifacts_subtype_allowed",
        "artifacts",
        f"subtype IS NULL OR subtype IN ({allowed})",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_artifacts_subtype_allowed",
        "artifacts",
        type_="check",
    )
    op.drop_table("device_spend")
    op.drop_index("idx_chatbot_messages_session", table_name="chatbot_messages")
    op.drop_table("chatbot_messages")
    op.drop_index(
        "idx_chatbot_sessions_device_created",
        table_name="chatbot_sessions",
    )
    op.drop_table("chatbot_sessions")
