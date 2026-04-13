"""Initial pipeline tables.

Revision ID: 001
Revises:
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Independent tables first
    op.create_table(
        "works",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sefaria_index_title", sa.Text, unique=True, nullable=False),
        sa.Column("common_name", sa.Text),
        sa.Column("level_1_name", sa.Text, nullable=False),
        sa.Column("level_2_name", sa.Text, nullable=False),
        sa.Column("level_3_name", sa.Text, nullable=False),
        sa.Column("language", sa.Text, server_default="he"),
        sa.Column("sefaria_metadata", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "artifact_types",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, unique=True, nullable=False),
        sa.Column("is_implemented", sa.Boolean, server_default="false"),
        sa.Column("description", sa.Text),
        sa.Column("config_schema", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("run_type", sa.Text, nullable=False),
        sa.Column("requested_scope", JSONB, nullable=False),
        sa.Column("actual_scope", JSONB),
        sa.Column("model_versions", JSONB),
        sa.Column("stages_status", JSONB),
        sa.Column("triggered_by", sa.Text),
        sa.Column("trigger_metadata", JSONB),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.Text, server_default="running"),
        sa.Column("error_message", sa.Text),
        sa.Column("pass_number", sa.Integer, server_default="1"),
    )

    op.create_table(
        "whatsapp_subscribers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("phone_number", sa.Text, unique=True, nullable=False),
        sa.Column("name", sa.Text),
        sa.Column("subscribed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status", sa.Text, server_default="active"),
        sa.Column("preferences", JSONB, server_default="{}"),
    )

    # Tables with FK to works
    op.create_table(
        "source_units",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("work_id", sa.Integer, sa.ForeignKey("works.id"), nullable=False),
        sa.Column("sefaria_ref", sa.Text, unique=True, nullable=False),
        sa.Column("level_1", sa.Text, nullable=False),
        sa.Column("level_2", sa.Text, nullable=False),
        sa.Column("level_3", sa.Text, nullable=False),
        sa.Column("hebrew_text", sa.Text, nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("work_id", "level_1", "level_2", "level_3"),
    )

    op.create_table(
        "classes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("teacher_name", sa.Text),
        sa.Column("rss_feed_url", sa.Text, unique=True, nullable=False),
        sa.Column("work_id", sa.Integer, sa.ForeignKey("works.id")),
        sa.Column("current_level_1", sa.Text),
        sa.Column("current_level_2", sa.Text),
        sa.Column("current_level_3", sa.Text),
        sa.Column("artifact_planning_trigger", sa.Text, server_default="auto"),
        sa.Column("always_override_artifact_plan", sa.Boolean, server_default="false"),
        sa.Column("whatsapp_blast_timing", sa.Text, server_default="immediate"),
        sa.Column("whatsapp_opt_in", sa.Boolean, server_default="true"),
        sa.Column("status", sa.Text, server_default="active"),
        sa.Column("config_overrides", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Episodes
    op.create_table(
        "episodes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("guid", sa.Text, unique=True, nullable=False),
        sa.Column("class_id", sa.Integer, sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("title", sa.Text),
        sa.Column("audio_url", sa.Text),
        sa.Column("local_audio_path", sa.Text),
        sa.Column("s3_audio_key", sa.Text),
        sa.Column("video_url", sa.Text),
        sa.Column("s3_video_key", sa.Text),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.Text, server_default="pending"),
        sa.Column("error_message", sa.Text),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Transcripts
    op.create_table(
        "transcripts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("episode_id", sa.Integer, sa.ForeignKey("episodes.id"), nullable=False),
        sa.Column("transcript_type", sa.Text, nullable=False),
        sa.Column("provider", sa.Text),
        sa.Column("s3_key", sa.Text),
        sa.Column("full_text", sa.Text),
        sa.Column("words", JSONB),
        sa.Column("language", sa.Text, server_default="he"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Alignments
    op.create_table(
        "alignments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("episode_id", sa.Integer, sa.ForeignKey("episodes.id"), nullable=False),
        sa.Column("source_unit_id", sa.Integer, sa.ForeignKey("source_units.id"), nullable=False),
        sa.Column("transcript_id", sa.Integer, sa.ForeignKey("transcripts.id"), nullable=False),
        sa.Column("start_ms", sa.Integer),
        sa.Column("end_ms", sa.Integer),
        sa.Column("position_in_unit", sa.Float),
        sa.Column("confidence_score", sa.Float),
        sa.Column("alignment_method", sa.Text),
        sa.Column("is_primary_reference", sa.Boolean, server_default="true"),
        sa.Column("is_digression", sa.Boolean, server_default="false"),
        sa.Column("is_intentional_skip", sa.Boolean, server_default="false"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Artifact plans
    op.create_table(
        "artifact_plans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_unit_id", sa.Integer, sa.ForeignKey("source_units.id"), nullable=False),
        sa.Column("origin_class_id", sa.Integer, sa.ForeignKey("classes.id")),
        sa.Column("is_override", sa.Boolean, server_default="false"),
        sa.Column("plan_items", JSONB, nullable=False),
        sa.Column("llm_model", sa.Text),
        sa.Column("llm_prompt_version", sa.Text),
        sa.Column("existing_artifacts_context", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
    )

    # Artifacts (no current_version_id FK yet — added after artifact_versions)
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_unit_id", sa.Integer, sa.ForeignKey("source_units.id"), nullable=False),
        sa.Column("class_id", sa.Integer, sa.ForeignKey("classes.id")),
        sa.Column("artifact_type_id", sa.Integer, sa.ForeignKey("artifact_types.id"), nullable=False),
        sa.Column("artifact_plan_id", sa.Integer, sa.ForeignKey("artifact_plans.id")),
        sa.Column("pipeline_run_id", sa.Integer, sa.ForeignKey("pipeline_runs.id")),
        sa.Column("subtype", sa.Text),
        sa.Column("priority", sa.Integer, nullable=False),
        sa.Column("position", sa.Float, nullable=False),
        sa.Column("status", sa.Text, server_default="planned"),
        sa.Column("current_version_id", sa.Integer),  # FK added later
        sa.Column("pass_number", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Artifact versions (references artifacts)
    op.create_table(
        "artifact_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("artifact_id", sa.Integer, sa.ForeignKey("artifacts.id"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("pipeline_run_id", sa.Integer, sa.ForeignKey("pipeline_runs.id")),
        sa.Column("parent_version_id", sa.Integer, sa.ForeignKey("artifact_versions.id")),
        sa.Column("s3_key", sa.Text),
        sa.Column("url", sa.Text),
        sa.Column("generation_prompt", sa.Text),
        sa.Column("context_mode", sa.Text),
        sa.Column("context_snapshot", JSONB),
        sa.Column("style_name", sa.Text),
        sa.Column("style_source", sa.Text),
        sa.Column("style_override", sa.Boolean, server_default="false"),
        sa.Column("llm_model", sa.Text),
        sa.Column("image_model", sa.Text),
        sa.Column("generation_metadata", JSONB),
        sa.Column("status", sa.Text, server_default="generated"),
        sa.Column("vote_session_id", sa.Integer),  # FK added later
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("artifact_id", "version_number"),
    )

    # Vote sessions (references artifact_versions)
    op.create_table(
        "vote_sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("artifact_version_id", sa.Integer, sa.ForeignKey("artifact_versions.id"), nullable=False),
        sa.Column("telegram_message_id", sa.Integer),
        sa.Column("telegram_chat_id", sa.Integer),
        sa.Column("voting_opened_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("voting_window_hours", sa.Integer),
        sa.Column("voting_closed_at", sa.DateTime(timezone=True)),
        sa.Column("upvotes_count", sa.Integer, server_default="0"),
        sa.Column("downvotes_count", sa.Integer, server_default="0"),
        sa.Column("approval_percentage", sa.Float),
        sa.Column("status", sa.Text, server_default="open"),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
    )

    # Now add deferred FKs for circular references
    op.create_foreign_key(
        "fk_artifact_versions_vote_session",
        "artifact_versions", "vote_sessions",
        ["vote_session_id"], ["id"],
    )

    # Votes
    op.create_table(
        "votes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("vote_session_id", sa.Integer, sa.ForeignKey("vote_sessions.id"), nullable=False),
        sa.Column("telegram_user_id", sa.Integer, nullable=False),
        sa.Column("telegram_username", sa.Text),
        sa.Column("vote_type", sa.String(10)),
        sa.Column("voted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("vote_session_id", "telegram_user_id"),
    )

    # Edit requests
    op.create_table(
        "edit_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("vote_session_id", sa.Integer, sa.ForeignKey("vote_sessions.id"), nullable=False),
        sa.Column("artifact_version_id", sa.Integer, sa.ForeignKey("artifact_versions.id"), nullable=False),
        sa.Column("telegram_message_id", sa.Integer),
        sa.Column("telegram_user_id", sa.Integer, nullable=False),
        sa.Column("telegram_username", sa.Text),
        sa.Column("raw_message", sa.Text, nullable=False),
        sa.Column("request_type", sa.Text),
        sa.Column("parsed_edit", JSONB),
        sa.Column("style_override_name", sa.Text),
        sa.Column("status", sa.Text, server_default="pending"),
        sa.Column("clarification_message", sa.Text),
        sa.Column("resulting_version_id", sa.Integer, sa.ForeignKey("artifact_versions.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Context syntheses
    op.create_table(
        "context_syntheses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_unit_id", sa.Integer, sa.ForeignKey("source_units.id"), nullable=False),
        sa.Column("class_id", sa.Integer, sa.ForeignKey("classes.id")),
        sa.Column("synthesis_text", sa.Text, nullable=False),
        sa.Column("llm_model", sa.Text),
        sa.Column("input_hash", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
    )

    # WhatsApp deliveries
    op.create_table(
        "whatsapp_deliveries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("artifact_version_id", sa.Integer, sa.ForeignKey("artifact_versions.id"), nullable=False),
        sa.Column("subscriber_id", sa.Integer, sa.ForeignKey("whatsapp_subscribers.id"), nullable=False),
        sa.Column("whatsapp_message_id", sa.Text),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("delivery_status", sa.Text),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text),
    )

    # Reconciliation flags
    op.create_table(
        "reconciliation_flags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("artifact_id", sa.Integer, sa.ForeignKey("artifacts.id"), nullable=False),
        sa.Column("artifact_version_id", sa.Integer, sa.ForeignKey("artifact_versions.id")),
        sa.Column("flag_type", sa.Text, nullable=False),
        sa.Column("reason", sa.Text),
        sa.Column("llm_recommendation", sa.Text),
        sa.Column("status", sa.Text, server_default="open"),
        sa.Column("requires_human_approval", sa.Boolean, server_default="true"),
        sa.Column("resolved_by", sa.Text),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed artifact types
    op.execute("""
        INSERT INTO artifact_types (name, is_implemented, description) VALUES
            ('image', TRUE, 'Generated image: illustration, diagram, infographic, chart, timeline, map'),
            ('video', FALSE, 'Generated video (future)'),
            ('text', FALSE, 'Generated text snippet or summary (future)'),
            ('interactive', FALSE, 'Interactive chart or graph (future)')
    """)


def downgrade() -> None:
    op.drop_table("reconciliation_flags")
    op.drop_table("whatsapp_deliveries")
    op.drop_table("context_syntheses")
    op.drop_table("edit_requests")
    op.drop_table("votes")
    op.drop_constraint("fk_artifact_versions_vote_session", "artifact_versions", type_="foreignkey")
    op.drop_table("vote_sessions")
    op.drop_table("artifact_versions")
    op.drop_table("artifacts")
    op.drop_table("artifact_plans")
    op.drop_table("alignments")
    op.drop_table("transcripts")
    op.drop_table("episodes")
    op.drop_table("classes")
    op.drop_table("source_units")
    op.drop_table("whatsapp_subscribers")
    op.drop_table("pipeline_runs")
    op.drop_table("artifact_types")
    op.drop_table("works")
