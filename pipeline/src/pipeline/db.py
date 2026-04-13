"""SQLAlchemy models for the pipeline database tables."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


# --- 3.1 Works & Source Units ---


class Work(Base):
    __tablename__ = "works"

    id = Column(Integer, primary_key=True)
    sefaria_index_title = Column(Text, unique=True, nullable=False)
    common_name = Column(Text)
    level_1_name = Column(Text, nullable=False)
    level_2_name = Column(Text, nullable=False)
    level_3_name = Column(Text, nullable=False)
    language = Column(Text, default="he")
    sefaria_metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

    source_units = relationship("SourceUnit", back_populates="work")
    classes = relationship("Class", back_populates="work")


class SourceUnit(Base):
    __tablename__ = "source_units"

    id = Column(Integer, primary_key=True)
    work_id = Column(Integer, ForeignKey("works.id"), nullable=False)
    sefaria_ref = Column(Text, unique=True, nullable=False)
    level_1 = Column(Text, nullable=False)
    level_2 = Column(Text, nullable=False)
    level_3 = Column(Text, nullable=False)
    hebrew_text = Column(Text, nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    work = relationship("Work", back_populates="source_units")
    alignments = relationship("Alignment", back_populates="source_unit")
    artifact_plans = relationship("ArtifactPlan", back_populates="source_unit")
    artifacts = relationship("Artifact", back_populates="source_unit")
    context_syntheses = relationship("ContextSynthesis", back_populates="source_unit")

    __table_args__ = (
        UniqueConstraint("work_id", "level_1", "level_2", "level_3"),
    )


# --- 3.2 Classes & Episodes ---


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    teacher_name = Column(Text)
    rss_feed_url = Column(Text, unique=True, nullable=False)
    work_id = Column(Integer, ForeignKey("works.id"))
    current_level_1 = Column(Text)
    current_level_2 = Column(Text)
    current_level_3 = Column(Text)
    artifact_planning_trigger = Column(Text, default="auto")
    always_override_artifact_plan = Column(Boolean, default=False)
    whatsapp_blast_timing = Column(Text, default="immediate")
    whatsapp_opt_in = Column(Boolean, default=True)
    status = Column(Text, default="active")
    config_overrides = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    work = relationship("Work", back_populates="classes")
    episodes = relationship("Episode", back_populates="klass")
    artifacts = relationship("Artifact", back_populates="klass")


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True)
    guid = Column(Text, unique=True, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    title = Column(Text)
    audio_url = Column(Text)
    local_audio_path = Column(Text)
    s3_audio_key = Column(Text)
    video_url = Column(Text)
    s3_video_key = Column(Text)
    published_at = Column(DateTime)
    status = Column(Text, default="pending")
    error_message = Column(Text)
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    klass = relationship("Class", back_populates="episodes")
    transcripts = relationship("Transcript", back_populates="episode")
    alignments = relationship("Alignment", back_populates="episode")


# --- 3.3 Transcripts & Alignment ---


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=False)
    transcript_type = Column(Text, nullable=False)
    provider = Column(Text)
    s3_key = Column(Text)
    full_text = Column(Text)
    words = Column(JSONB)
    language = Column(Text, default="he")
    created_at = Column(DateTime, default=datetime.utcnow)

    episode = relationship("Episode", back_populates="transcripts")
    alignments = relationship("Alignment", back_populates="transcript")


class Alignment(Base):
    __tablename__ = "alignments"

    id = Column(Integer, primary_key=True)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=False)
    source_unit_id = Column(Integer, ForeignKey("source_units.id"), nullable=False)
    transcript_id = Column(Integer, ForeignKey("transcripts.id"), nullable=False)
    start_ms = Column(Integer)
    end_ms = Column(Integer)
    position_in_unit = Column(Float)
    confidence_score = Column(Float)
    alignment_method = Column(Text)
    is_primary_reference = Column(Boolean, default=True)
    is_digression = Column(Boolean, default=False)
    is_intentional_skip = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    episode = relationship("Episode", back_populates="alignments")
    source_unit = relationship("SourceUnit", back_populates="alignments")
    transcript = relationship("Transcript", back_populates="alignments")


# --- 3.4 Artifact Type Registry ---


class ArtifactType(Base):
    __tablename__ = "artifact_types"

    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    is_implemented = Column(Boolean, default=False)
    description = Column(Text)
    config_schema = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

    artifacts = relationship("Artifact", back_populates="artifact_type")


# --- 3.5 Artifact Plans ---


class ArtifactPlan(Base):
    __tablename__ = "artifact_plans"

    id = Column(Integer, primary_key=True)
    source_unit_id = Column(Integer, ForeignKey("source_units.id"), nullable=False)
    origin_class_id = Column(Integer, ForeignKey("classes.id"))
    is_override = Column(Boolean, default=False)
    plan_items = Column(JSONB, nullable=False)
    llm_model = Column(Text)
    llm_prompt_version = Column(Text)
    existing_artifacts_context = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    superseded_at = Column(DateTime)

    source_unit = relationship("SourceUnit", back_populates="artifact_plans")


# --- 3.6 Artifacts & Versions ---


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True)
    source_unit_id = Column(Integer, ForeignKey("source_units.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"))
    artifact_type_id = Column(Integer, ForeignKey("artifact_types.id"), nullable=False)
    artifact_plan_id = Column(Integer, ForeignKey("artifact_plans.id"))
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id"))
    subtype = Column(Text)
    priority = Column(Integer, nullable=False)
    position = Column(Float, nullable=False)
    status = Column(Text, default="planned")
    current_version_id = Column(Integer)
    pass_number = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    source_unit = relationship("SourceUnit", back_populates="artifacts")
    klass = relationship("Class", back_populates="artifacts")
    artifact_type = relationship("ArtifactType", back_populates="artifacts")
    versions = relationship("ArtifactVersion", back_populates="artifact")


class ArtifactVersion(Base):
    __tablename__ = "artifact_versions"

    id = Column(Integer, primary_key=True)
    artifact_id = Column(Integer, ForeignKey("artifacts.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id"))
    parent_version_id = Column(Integer, ForeignKey("artifact_versions.id"))
    s3_key = Column(Text)
    url = Column(Text)
    generation_prompt = Column(Text)
    context_mode = Column(Text)
    context_snapshot = Column(JSONB)
    style_name = Column(Text)
    style_source = Column(Text)
    style_override = Column(Boolean, default=False)
    llm_model = Column(Text)
    image_model = Column(Text)
    generation_metadata = Column(JSONB)
    status = Column(Text, default="generated")
    vote_session_id = Column(Integer, ForeignKey("vote_sessions.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    artifact = relationship("Artifact", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("artifact_id", "version_number"),
    )


# --- 3.7 Pipeline Runs ---


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True)
    run_type = Column(Text, nullable=False)
    requested_scope = Column(JSONB, nullable=False)
    actual_scope = Column(JSONB)
    model_versions = Column(JSONB)
    stages_status = Column(JSONB)
    triggered_by = Column(Text)
    trigger_metadata = Column(JSONB)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(Text, default="running")
    error_message = Column(Text)
    pass_number = Column(Integer, default=1)


# --- 3.8 Telegram Voting ---


class VoteSession(Base):
    __tablename__ = "vote_sessions"

    id = Column(Integer, primary_key=True)
    artifact_version_id = Column(Integer, ForeignKey("artifact_versions.id"), nullable=False)
    telegram_message_id = Column(Integer)
    telegram_chat_id = Column(Integer)
    voting_opened_at = Column(DateTime, default=datetime.utcnow)
    voting_window_hours = Column(Integer)
    voting_closed_at = Column(DateTime)
    upvotes_count = Column(Integer, default=0)
    downvotes_count = Column(Integer, default=0)
    approval_percentage = Column(Float)
    status = Column(Text, default="open")
    approved_at = Column(DateTime)

    votes = relationship("Vote", back_populates="vote_session")
    edit_requests = relationship("EditRequest", back_populates="vote_session")


class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True)
    vote_session_id = Column(Integer, ForeignKey("vote_sessions.id"), nullable=False)
    telegram_user_id = Column(Integer, nullable=False)
    telegram_username = Column(Text)
    vote_type = Column(String(10))
    voted_at = Column(DateTime, default=datetime.utcnow)

    vote_session = relationship("VoteSession", back_populates="votes")

    __table_args__ = (
        UniqueConstraint("vote_session_id", "telegram_user_id"),
    )


class EditRequest(Base):
    __tablename__ = "edit_requests"

    id = Column(Integer, primary_key=True)
    vote_session_id = Column(Integer, ForeignKey("vote_sessions.id"), nullable=False)
    artifact_version_id = Column(Integer, ForeignKey("artifact_versions.id"), nullable=False)
    telegram_message_id = Column(Integer)
    telegram_user_id = Column(Integer, nullable=False)
    telegram_username = Column(Text)
    raw_message = Column(Text, nullable=False)
    request_type = Column(Text)
    parsed_edit = Column(JSONB)
    style_override_name = Column(Text)
    status = Column(Text, default="pending")
    clarification_message = Column(Text)
    resulting_version_id = Column(Integer, ForeignKey("artifact_versions.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    vote_session = relationship("VoteSession", back_populates="edit_requests")


# --- Context Synthesis Cache ---


class ContextSynthesis(Base):
    __tablename__ = "context_syntheses"

    id = Column(Integer, primary_key=True)
    source_unit_id = Column(Integer, ForeignKey("source_units.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"))
    synthesis_text = Column(Text, nullable=False)
    llm_model = Column(Text)
    input_hash = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    invalidated_at = Column(DateTime)

    source_unit = relationship("SourceUnit", back_populates="context_syntheses")


# --- WhatsApp ---


class WhatsAppSubscriber(Base):
    __tablename__ = "whatsapp_subscribers"

    id = Column(Integer, primary_key=True)
    phone_number = Column(Text, unique=True, nullable=False)
    name = Column(Text)
    subscribed_at = Column(DateTime, default=datetime.utcnow)
    status = Column(Text, default="active")
    preferences = Column(JSONB, default={})


class WhatsAppDelivery(Base):
    __tablename__ = "whatsapp_deliveries"

    id = Column(Integer, primary_key=True)
    artifact_version_id = Column(Integer, ForeignKey("artifact_versions.id"), nullable=False)
    subscriber_id = Column(Integer, ForeignKey("whatsapp_subscribers.id"), nullable=False)
    whatsapp_message_id = Column(Text)
    sent_at = Column(DateTime)
    delivery_status = Column(Text)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text)


# --- Reconciliation ---


class ReconciliationFlag(Base):
    __tablename__ = "reconciliation_flags"

    id = Column(Integer, primary_key=True)
    artifact_id = Column(Integer, ForeignKey("artifacts.id"), nullable=False)
    artifact_version_id = Column(Integer, ForeignKey("artifact_versions.id"))
    flag_type = Column(Text, nullable=False)
    reason = Column(Text)
    llm_recommendation = Column(Text)
    status = Column(Text, default="open")
    requires_human_approval = Column(Boolean, default=True)
    resolved_by = Column(Text)
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# --- Engine ---


def get_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True)


def get_session_factory(database_url: str) -> sessionmaker[Session]:
    engine = get_engine(database_url)
    return sessionmaker(bind=engine)


def create_tables(database_url: str):
    """Create all tables. For dev/testing only — production uses Alembic."""
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
