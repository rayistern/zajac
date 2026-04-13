# Master Implementation Plan
## Hebrew Podcast Pipeline — Torah Content Generation System

---

## Table of Contents

1. [Glossary](#glossary)
2. [System Overview](#system-overview)
3. [Database Schema](#database-schema)
4. [Configuration Structure](#configuration-structure)
5. [Phase 0 — Foundation & Infrastructure](#phase-0)
6. [Phase 1 — Ingestion & Transcription](#phase-1)
7. [Phase 2 — Sefaria Integration & Text Alignment](#phase-2)
8. [Phase 3 — Artifact Planning](#phase-3)
9. [Phase 4 — Image Generation](#phase-4)
10. [Phase 5 — Telegram Voting & Edit Workflow](#phase-5)
11. [Phase 6 — WhatsApp Distribution](#phase-6)
12. [Phase 7 — Artifact Lifecycle Management](#phase-7)
13. [Phase 8 — AWS Deployment](#phase-8)
14. [Logging & Observability](#logging)
15. [Out of Scope / Future Phases](#future)
16. [Open Questions](#open-questions)

---

## 1. Glossary <a name="glossary"></a>

These terms are used precisely throughout this document. Do not substitute or conflate them.

| Term | Definition |
|---|---|
| **Work** | A Torah text registered in Sefaria (e.g. Mishneh Torah, Chumash, Mishnah, Talmud Bavli) |
| **Source Unit** | The atomic unit of a Work as defined by that Work's hierarchy (e.g. a Halacha in Rambam, a Verse in Chumash, a Mishna in Mishnah). Always level_1 / level_2 / level_3 in the DB. |
| **Halacha** | A Source Unit specifically within Mishneh Torah. Used colloquially in this doc but the DB models it generically. |
| **Class** | A podcast RSS feed taught by one teacher on one Work or section thereof |
| **Episode** | A single audio episode from a Class RSS feed |
| **Transcript** | The text output of transcribing an Episode (primary = sofer.ai; timestamped = Whisper; merged = both combined) |
| **Alignment** | The mapping of a Transcript segment to one or more Source Units |
| **Artifact Plan** | The LLM-generated manifest for a Source Unit declaring what artifacts should exist (type, priority, position, reason) |
| **Artifact** | Any generated content item tied to a Source Unit: image, video, text snippet, interactive chart, etc. |
| **Artifact Type** | A registered type in the `artifact_types` table (e.g. `image`, `video`, `text`, `interactive`) |
| **Artifact Version** | A specific generated instance of an Artifact. Multiple versions can exist (edits, re-runs, style overrides). |
| **Pipeline Run** | A logged execution of the pipeline, full or partial, with defined scope, model versions, and per-stage status |
| **Artifact Lifecycle** | `planned → ordered → generated → in_review → approved → published → hidden` or `rejected` |
| **Style** | A named image generation preset (e.g. `photorealistic`, `watercolor`, `cartoon`) with its own system prompt snippet |

---

## 2. System Overview <a name="system-overview"></a>

### End-to-End Flow

```
RSS Feeds (multiple classes)
    │
    ▼
Episode Download
    │
    ▼
Dual Transcription
  ├── sofer.ai (accurate Hebrew, no timestamps)
  └── Whisper (timestamps, word-level)
    │
    ▼
Transcript Merge (accurate text + timestamps)
    │
    ▼
Sefaria Text Fetch (original Hebrew, canonical refs)
    │
    ▼
4-Pass LLM Alignment (transcript → source units)
  ├── Pass 1: Header detection (spoken "halacha 5", "הלכה ט")
  ├── Pass 2: Gap detection (missing source units)
  ├── Pass 3: Content matching (semantic alignment)
  └── Pass 4: Verification
    │
    ▼
Artifact Planning Pass (per source unit, LLM)
  └── Produces manifest: [{type, priority, position, reason, prompt_focus}]
    │
    ▼
Artifact Generation (per planned item, per type pipeline)
  ├── Image Pipeline (Phase 4)
  ├── Video Pipeline (future)
  ├── Text Pipeline (future)
  └── Interactive Pipeline (future)
    │
    ▼
Telegram Voting Group
  ├── Volunteer reactions (upvote / downvote)
  ├── Volunteer edit requests (reply → re-generate → re-vote)
  └── Volunteer style overrides (/style <name> → re-generate → re-vote)
    │
    ▼
Approval Tally (configurable thresholds)
    │
    ▼
WhatsApp Blast (approved artifacts → active subscribers)
    │
    ▼
Delivery Tracking
```

### Key Architectural Principles

- **Source of truth is Sefaria.** Transcripts map back to the canonical text, never the reverse.
- **Everything configurable.** No hardcoded thresholds, prompts, providers, or timings. All in `config.yaml`.
- **Idempotent operations.** Every stage can be re-run without producing duplicates.
- **Separation of concerns.** Each stage is independently retriable, testable, and replaceable.
- **Generic artifact system.** Images are one artifact type. The DB and pipeline support any future type without schema changes.
- **Full observability.** Structured JSON logging with correlation IDs across all stages and services.

---

## 3. Database Schema <a name="database-schema"></a>

### 3.1 Works & Source Units (All of Torah)

```sql
-- Registry of Torah works (Rambam, Chumash, Mishnah, etc.)
CREATE TABLE works (
    id SERIAL PRIMARY KEY,
    sefaria_index_title TEXT UNIQUE NOT NULL,  -- Sefaria canonical title
    common_name TEXT,                           -- "Rambam", "Chumash"
    level_1_name TEXT NOT NULL,                 -- e.g. "Book", "Tractate"
    level_2_name TEXT NOT NULL,                 -- e.g. "Chapter", "Parasha"
    level_3_name TEXT NOT NULL,                 -- e.g. "Halacha", "Verse", "Mishna"
    language TEXT DEFAULT 'he',
    sefaria_metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Atomic source units (halachot, verses, mishnayot, etc.)
CREATE TABLE source_units (
    id SERIAL PRIMARY KEY,
    work_id INTEGER NOT NULL REFERENCES works(id),
    sefaria_ref TEXT UNIQUE NOT NULL,   -- e.g. "Mishneh Torah, Shabbat 3:5"
    level_1 TEXT NOT NULL,              -- e.g. "Shabbat" (Book)
    level_2 TEXT NOT NULL,              -- e.g. "3" (Chapter)
    level_3 TEXT NOT NULL,              -- e.g. "5" (Halacha)
    hebrew_text TEXT NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(work_id, level_1, level_2, level_3)
);
```

### 3.2 Classes & Episodes

```sql
CREATE TABLE classes (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    teacher_name TEXT,
    rss_feed_url TEXT UNIQUE NOT NULL,
    work_id INTEGER REFERENCES works(id),
    current_level_1 TEXT,               -- current book/tractate
    current_level_2 TEXT,               -- current chapter
    current_level_3 TEXT,               -- current halacha/verse
    artifact_planning_trigger TEXT DEFAULT 'auto', -- 'auto' | 'manual'
    always_override_artifact_plan BOOLEAN DEFAULT FALSE,
    whatsapp_blast_timing TEXT DEFAULT 'immediate', -- 'immediate' | 'scheduled'
    whatsapp_opt_in BOOLEAN DEFAULT TRUE,  -- whether subscribers receive this class
    status TEXT DEFAULT 'active',
    config_overrides JSONB DEFAULT '{}',   -- per-class config overrides
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE episodes (
    id SERIAL PRIMARY KEY,
    guid TEXT UNIQUE NOT NULL,
    class_id INTEGER NOT NULL REFERENCES classes(id),
    title TEXT,
    audio_url TEXT,
    local_audio_path TEXT,
    s3_audio_key TEXT,
    video_url TEXT,                        -- original video if class includes talking-head video
    s3_video_key TEXT,
    published_at TIMESTAMPTZ,
    status TEXT DEFAULT 'pending',         -- pending | processing | done | error
    error_message TEXT,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.3 Transcripts & Alignment

```sql
CREATE TABLE transcripts (
    id SERIAL PRIMARY KEY,
    episode_id INTEGER NOT NULL REFERENCES episodes(id),
    transcript_type TEXT NOT NULL,  -- 'primary' | 'timestamped' | 'merged'
    provider TEXT,                  -- 'sofer_ai' | 'openai_whisper' | 'merged'
    s3_key TEXT,
    full_text TEXT,
    words JSONB,                    -- [{word, start_ms, end_ms}]
    language TEXT DEFAULT 'he',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE alignments (
    id SERIAL PRIMARY KEY,
    episode_id INTEGER NOT NULL REFERENCES episodes(id),
    source_unit_id INTEGER NOT NULL REFERENCES source_units(id),
    transcript_id INTEGER NOT NULL REFERENCES transcripts(id),
    start_ms INTEGER,
    end_ms INTEGER,
    position_in_unit FLOAT,          -- 0.0-1.0, where in the source unit this segment falls
    confidence_score FLOAT,
    alignment_method TEXT,           -- 'header_detection' | 'content_match' | 'gap_fill' | 'manual'
    is_primary_reference BOOLEAN DEFAULT TRUE,  -- false = cross-reference, not primary topic
    is_digression BOOLEAN DEFAULT FALSE,
    is_intentional_skip BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.4 Artifact Type Registry

```sql
CREATE TABLE artifact_types (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,       -- 'image' | 'video' | 'text' | 'interactive'
    is_implemented BOOLEAN DEFAULT FALSE,
    description TEXT,
    config_schema JSONB,             -- JSON schema for type-specific config
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed data
INSERT INTO artifact_types (name, is_implemented, description) VALUES
    ('image', TRUE, 'Generated image: illustration, diagram, infographic, chart, timeline, map'),
    ('video', FALSE, 'Generated video (future)'),
    ('text', FALSE, 'Generated text snippet or summary (future)'),
    ('interactive', FALSE, 'Interactive chart or graph (future)');
```

### 3.5 Artifact Plans

```sql
CREATE TABLE artifact_plans (
    id SERIAL PRIMARY KEY,
    source_unit_id INTEGER NOT NULL REFERENCES source_units(id),
    origin_class_id INTEGER REFERENCES classes(id),   -- NULL = base shared plan
    is_override BOOLEAN DEFAULT FALSE,
    plan_items JSONB NOT NULL,      -- [{type, subtype, priority, position, reason, prompt_focus, context_mode}]
    llm_model TEXT,
    llm_prompt_version TEXT,
    existing_artifacts_context JSONB, -- snapshot of existing artifacts shown to planner
    created_at TIMESTAMPTZ DEFAULT NOW(),
    superseded_at TIMESTAMPTZ         -- set when a newer plan replaces this one
);
```

### 3.6 Artifacts & Versions

```sql
CREATE TABLE artifacts (
    id SERIAL PRIMARY KEY,
    source_unit_id INTEGER NOT NULL REFERENCES source_units(id),
    class_id INTEGER REFERENCES classes(id),  -- which class prompted generation
    artifact_type_id INTEGER NOT NULL REFERENCES artifact_types(id),
    artifact_plan_id INTEGER REFERENCES artifact_plans(id),
    pipeline_run_id INTEGER REFERENCES pipeline_runs(id),
    subtype TEXT,                   -- e.g. 'illustration' | 'diagram' | 'infographic' | 'chart' | 'timeline'
    priority INTEGER NOT NULL,      -- within this source unit (1 = highest)
    position FLOAT NOT NULL,        -- 0.0-1.0, position within source unit
    status TEXT DEFAULT 'planned',  -- planned | ordered | generated | in_review | approved | rejected | published | hidden
    current_version_id INTEGER,     -- FK to artifact_versions (set after first generation)
    pass_number INTEGER DEFAULT 1,  -- which generation pass produced this
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE artifact_versions (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER NOT NULL REFERENCES artifacts(id),
    version_number INTEGER NOT NULL,
    pipeline_run_id INTEGER REFERENCES pipeline_runs(id),
    parent_version_id INTEGER REFERENCES artifact_versions(id),
    s3_key TEXT,
    url TEXT,
    generation_prompt TEXT,
    context_mode TEXT,              -- 'FULL' | 'SYNTHESIZED'
    context_snapshot JSONB,         -- what was actually sent to the generator
    style_name TEXT,                -- e.g. 'photorealistic', 'watercolor'
    style_source TEXT,              -- 'random_rotation' | 'telegram_override' | 'config_default'
    style_override BOOLEAN DEFAULT FALSE,
    llm_model TEXT,
    image_model TEXT,
    generation_metadata JSONB,
    status TEXT DEFAULT 'generated', -- generated | in_review | approved | rejected | published | hidden
    vote_session_id INTEGER REFERENCES vote_sessions(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(artifact_id, version_number)
);

-- Back-fill FK (circular ref resolved after both tables exist)
ALTER TABLE artifacts ADD CONSTRAINT fk_current_version
    FOREIGN KEY (current_version_id) REFERENCES artifact_versions(id) DEFERRABLE;
```

### 3.7 Pipeline Runs

```sql
CREATE TABLE pipeline_runs (
    id SERIAL PRIMARY KEY,
    run_type TEXT NOT NULL,           -- 'full' | 'partial'
    requested_scope JSONB NOT NULL,   -- what was requested: {stages, class_ids, source_unit_ids, etc.}
    actual_scope JSONB,               -- what actually ran (may differ if partial failed)
    model_versions JSONB,             -- {transcription: '...', alignment: '...', image: '...'}
    stages_status JSONB,              -- {transcription: 'done', alignment: 'error', ...}
    triggered_by TEXT,                -- 'auto' | 'cli' | 'api'
    trigger_metadata JSONB,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT DEFAULT 'running',    -- running | completed | partial | failed
    error_message TEXT,
    pass_number INTEGER DEFAULT 1     -- 1 = first generation, 2 = re-run with new models, etc.
);
```

### 3.8 Telegram Voting

```sql
CREATE TABLE vote_sessions (
    id SERIAL PRIMARY KEY,
    artifact_version_id INTEGER NOT NULL REFERENCES artifact_versions(id),
    telegram_message_id BIGINT,
    telegram_chat_id BIGINT,
    voting_opened_at TIMESTAMPTZ DEFAULT NOW(),
    voting_window_hours INTEGER,
    voting_closed_at TIMESTAMPTZ,
    upvotes_count INTEGER DEFAULT 0,
    downvotes_count INTEGER DEFAULT 0,
    approval_percentage FLOAT,
    status TEXT DEFAULT 'open',       -- open | closed | approved | rejected
    approved_at TIMESTAMPTZ
);

CREATE TABLE votes (
    id SERIAL PRIMARY KEY,
    vote_session_id INTEGER NOT NULL REFERENCES vote_sessions(id),
    telegram_user_id BIGINT NOT NULL,
    telegram_username TEXT,
    vote_type TEXT CHECK (vote_type IN ('upvote', 'downvote')),
    voted_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(vote_session_id, telegram_user_id)
);

CREATE TABLE edit_requests (
    id SERIAL PRIMARY KEY,
    vote_session_id INTEGER NOT NULL REFERENCES vote_sessions(id),
    artifact_version_id INTEGER NOT NULL REFERENCES artifact_versions(id),
    telegram_message_id BIGINT,
    telegram_user_id BIGINT NOT NULL,
    telegram_username TEXT,
    raw_message TEXT NOT NULL,
    request_type TEXT,               -- 'style_override' | 'content_edit' | 'ambiguous' | 'noise'
    parsed_edit JSONB,               -- structured edit request after LLM parsing
    style_override_name TEXT,        -- if request_type = 'style_override'
    status TEXT DEFAULT 'pending',   -- pending | processing | applied | rejected_noise | clarification_needed
    clarification_message TEXT,
    resulting_version_id INTEGER REFERENCES artifact_versions(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.9 Frontend Timeline View

Artifacts live at the source unit (halacha) level. Their display timing within an episode is derived from the alignment window + position float. Rather than storing redundant timestamps on artifacts, a DB view pre-computes the display timeline for the frontend.

```sql
CREATE VIEW artifact_timeline AS
SELECT
    av.id                                          AS artifact_version_id,
    a.id                                           AS artifact_id,
    a.source_unit_id,
    su.sefaria_ref,
    al.episode_id,
    at.name                                        AS artifact_type,
    a.subtype,
    a.priority,
    a.position,
    av.style_name,
    av.url,
    av.status,
    al.start_ms + (a.position * (al.end_ms - al.start_ms))::INTEGER
                                                   AS display_start_ms,
    COALESCE(
        LEAD(
            al.start_ms + (a.position * (al.end_ms - al.start_ms))::INTEGER
        ) OVER (PARTITION BY al.episode_id ORDER BY
            al.start_ms + (a.position * (al.end_ms - al.start_ms))
        ),
        al.end_ms
    )                                              AS display_end_ms,
    al.start_ms                                    AS halacha_start_ms,
    al.end_ms                                      AS halacha_end_ms
FROM artifact_versions av
JOIN artifacts a          ON av.artifact_id = a.id
JOIN artifact_types at    ON a.artifact_type_id = at.id
JOIN source_units su      ON a.source_unit_id = su.id
JOIN alignments al        ON al.source_unit_id = a.source_unit_id
                         AND al.is_primary_reference = TRUE
WHERE av.status = 'published'
  AND av.id = a.current_version_id;
```

The frontend queries this view filtered by `episode_id` to get the full playback timeline in one call. Exact display duration semantics (how long an artifact stays visible, user interaction to pause/dismiss) are a Phase 2 UX design decision — see `PHASE_2_3_SPEC.md`.

### 3.10 Chatbot Context Package (Phase 3 prep)

The data needed for the Phase 3 chatbot exists already:
- `transcripts` (merged, word-level timestamps) — truncatable to current playback position
- `source_units` (active halacha text at current timestamp, via `artifact_timeline` view)
- `artifacts` + `artifact_versions` (what has been shown up to this point)
- `alignments` (which halachot have been covered)

No schema additions needed now. Context packaging logic is defined in Phase 3. See `PHASE_2_3_SPEC.md`.

### 3.11 Secondary & Commentary Texts (Phase 2)

Cross-work references (Talmudic sources, Rishonim commentary, etc.) are deferred to Phase 2. The `source_units` table handles one work per unit cleanly. Phase 2 will extend with a `source_unit_links` table for cross-references. See `PHASE_2_3_SPEC.md`.

### 3.12 Context Synthesis Cache

```sql
CREATE TABLE context_syntheses (
    id SERIAL PRIMARY KEY,
    source_unit_id INTEGER NOT NULL REFERENCES source_units(id),
    class_id INTEGER REFERENCES classes(id),  -- NULL = cross-class synthesis
    synthesis_text TEXT NOT NULL,
    llm_model TEXT,
    input_hash TEXT,                  -- hash of inputs; invalidated if source changes
    created_at TIMESTAMPTZ DEFAULT NOW(),
    invalidated_at TIMESTAMPTZ
);
```

### 3.10 WhatsApp

```sql
CREATE TABLE whatsapp_subscribers (
    id SERIAL PRIMARY KEY,
    phone_number TEXT UNIQUE NOT NULL,  -- E.164 format
    name TEXT,
    subscribed_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'active',       -- active | inactive | blocked
    preferences JSONB DEFAULT '{}'
);

CREATE TABLE whatsapp_deliveries (
    id SERIAL PRIMARY KEY,
    artifact_version_id INTEGER NOT NULL REFERENCES artifact_versions(id),
    subscriber_id INTEGER NOT NULL REFERENCES whatsapp_subscribers(id),
    whatsapp_message_id TEXT,
    sent_at TIMESTAMPTZ,
    delivery_status TEXT,              -- queued | sent | delivered | read | failed
    retry_count INTEGER DEFAULT 0,
    error_message TEXT
);
```

### 3.11 Artifact Reconciliation

```sql
-- LLM-flagged reconciliation issues
CREATE TABLE reconciliation_flags (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER NOT NULL REFERENCES artifacts(id),
    artifact_version_id INTEGER REFERENCES artifact_versions(id),
    flag_type TEXT NOT NULL,    -- 'stale_superseded' | 'orphaned' | 'duplicate_type' | 'never_published'
    reason TEXT,
    llm_recommendation TEXT,    -- 'hide' | 'review' | 'keep'
    status TEXT DEFAULT 'open', -- open | resolved | dismissed
    requires_human_approval BOOLEAN DEFAULT TRUE,  -- from config
    resolved_by TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. Configuration Structure <a name="configuration-structure"></a>

```yaml
# config.yaml — complete structure

pipeline:
  log_level: "INFO"
  log_format: "json"               # json | pretty
  state_db_url: "${DATABASE_URL}"  # PostgreSQL connection string

aws:
  region: "us-east-1"
  s3_bucket: "podcast-pipeline-assets"
  sqs_queue_url: "${SQS_QUEUE_URL}"

classes:
  - id: "cohen-hilchot-shabbat"
    name: "Rabbi Cohen — Hilchot Shabbat"
    teacher: "Rabbi Cohen"
    rss_feed_url: "${COHEN_RSS_URL}"
    sefaria_ref: "Mishneh Torah, Shabbat"
    artifact_planning_trigger: "auto"   # auto | manual
    always_override_artifact_plan: false
    whatsapp_blast_timing: "immediate"  # immediate | scheduled
    whatsapp_opt_in: true
    config_overrides:
      image_generation:
        styles_enabled: ["photorealistic", "watercolor"]

transcription:
  primary_provider: "sofer_ai"          # accurate Hebrew, no timestamps
  timestamp_provider: "openai_whisper"  # timestamps only

  sofer_ai:
    language: "he"
    model: "default"

  openai_whisper:
    model: "whisper-1"
    language: "he"
    response_format: "verbose_json"
    timestamp_granularities: ["word"]

  assemblyai:
    language_code: "he"

  deepgram:
    language: "he"
    model: "nova-2"

sefaria:
  base_url: "https://www.sefaria.org/api"
  use_mcp: true
  language: "he"
  cache_ttl_days: 30

text_alignment:
  llm:
    provider: "anthropic"
    model: "claude-sonnet-4-20250514"
  passes:
    header_detection: true
    gap_detection: true
    content_matching: true
    verification: true

artifact_planning:
  llm:
    provider: "anthropic"
    model: "claude-sonnet-4-20250514"
  max_artifacts_per_source_unit: 5
  context_mode: "SYNTHESIZED"         # FULL | SYNTHESIZED (default, overridable per class)
  show_existing_artifacts_to_planner: true

image_generation:
  provider: "replicate"               # replicate | openai | google_imagen (future)
  replicate:
    model: "black-forest-labs/flux-1.1-pro"

  context_mode: "SYNTHESIZED"         # FULL | SYNTHESIZED

  # System prompt approach — no string concatenation
  system_prompt_file: "./prompts/image_system_prompt.yaml"

  styles:
    enabled:
      - "photorealistic"
      - "watercolor"
      - "cartoon"
      - "line_art"
      - "oil_painting"
    rotation: "random_per_image"      # random_per_image | random_per_source_unit | fixed
    default: "photorealistic"         # fallback if rotation disabled
    allow_telegram_override: true

  per_subtype_models:
    illustration: "black-forest-labs/flux-1.1-pro"
    diagram: "openai/dall-e-3"
    infographic: "openai/dall-e-3"
    chart: "openai/dall-e-3"
    timeline: "openai/dall-e-3"
    map: "openai/dall-e-3"

telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  voting_group_chat_id: "${TELEGRAM_VOTING_CHAT_ID}"
  upvote_emoji: "👍"
  downvote_emoji: "👎"
  voting_window_hours: 24
  edit_request_validation: true       # run LLM classifier on replies before acting
  style_override_command: "/style"    # command prefix for style overrides

approval:
  min_approval_percentage: 70
  min_total_votes: 3
  require_both_criteria: true         # both % and min votes

whatsapp:
  business_phone_id: "${WHATSAPP_PHONE_ID}"
  rate_limit_per_second: 20
  retry_failed: true
  max_retries: 3

reconciliation:
  require_human_approval: true        # if false, LLM recommendation auto-applied
  auto_hide_stale_after_days: 90

retention:
  audio_files_days: 90
  transcripts_days: 365
  rejected_artifact_versions_days: 30
```

---

## 5. Phase 0 — Foundation & Infrastructure <a name="phase-0"></a>

### 0.1 PostgreSQL Setup

- Provision RDS PostgreSQL instance (or local Docker for dev)
- Run all migrations in order
- Set up connection pooling
- No SQLite anywhere — clean start

### 0.2 AWS Infrastructure (Terraform)

Files to create:
- `terraform/main.tf` — provider, S3, SQS, secrets
- `terraform/rds.tf` — PostgreSQL
- `terraform/ecs.tf` — Fargate cluster, task definitions
- `terraform/iam.tf` — roles and policies
- `terraform/eventbridge.tf` — cron schedules
- `terraform/variables.tf`
- `terraform/outputs.tf`

### 0.3 Core Modules

Files to create:
- `src/db.py` — PostgreSQL connection manager, pooling
- `src/storage.py` — S3 abstraction (upload, download, presigned URLs)
- `src/queue.py` — SQS job queue (send, receive, delete)
- `src/config.py` — config loader with per-class override merging
- `src/logger.py` — structured JSON logger with correlation ID support

### 0.4 Structured Logging

Every log entry includes:

```json
{
  "timestamp": "2025-01-01T10:00:00Z",
  "level": "INFO",
  "correlation_id": "uuid-per-pipeline-run",
  "stage": "alignment",
  "class_id": "cohen-hilchot-shabbat",
  "episode_id": 42,
  "source_unit_ref": "Mishneh Torah, Shabbat 3:5",
  "message": "Alignment confidence below threshold",
  "data": {}
}
```

Correlation ID is generated at pipeline run start and passed through all stages, services, and async jobs for that run.

### 0.5 Image Style System

File: `prompts/image_system_prompt.yaml`

```yaml
base: |
  You are a visual artist specializing in Jewish educational content.
  Your images must be respectful and appropriate for religious audiences.
  Free of text overlays, identifiable faces, or modern anachronisms.
  Symbolic and abstract when depicting Torah concepts.
  Aspect ratio: 16:9. Quality: high.

styles:
  photorealistic: |
    Style: Photorealistic. Dramatic cinematic lighting. Rich textures.
    Warm earth tones, deep blues, golden accents. Contemplative mood.

  watercolor: |
    Style: Soft watercolor illustration. Gentle washes of color.
    Flowing lines, translucent layers. Warm and spiritual atmosphere.

  cartoon: |
    Style: Clean editorial cartoon. Bold outlines, flat color fills.
    Friendly and educational tone. Simple symbolic imagery.

  line_art: |
    Style: Detailed pen and ink line art. Fine cross-hatching.
    Monochromatic or minimal color. Scholarly, archival quality.

  oil_painting: |
    Style: Classical oil painting. Rich impasto texture.
    Rembrandt-style lighting. Deep shadows, luminous highlights.
```

Style selection at generation time: pick randomly from `styles.enabled` list in config. If `allow_telegram_override: true`, accept `/style <name>` command from volunteers.

---

## 6. Phase 1 — Ingestion & Transcription <a name="phase-1"></a>

### 1.1 Multi-Class RSS Ingestion

File: `src/rss_parser.py` (refactor)

- Iterate over all `classes` in config
- Fetch each RSS feed
- Insert new episodes with `class_id`
- Skip already-processed guids (idempotent)

### 1.2 Audio Download

- Download to temp local path
- Upload to `s3://bucket/audio/{class_id}/{guid}.mp3`
- Store `s3_audio_key` on episode record
- Configurable: delete local after upload

### 1.3 Dual Transcription

File: `src/dual_transcriber.py`

Run in parallel:
1. **sofer.ai** — accurate Hebrew text, no timestamps → stored as `transcript_type: 'primary'`
2. **Whisper** — word-level timestamps → stored as `transcript_type: 'timestamped'`

Then merge:
- Use sofer.ai text as primary
- Align Whisper word timestamps to sofer.ai words via `SequenceMatcher`
- Produce merged transcript with accurate text + timestamps → `transcript_type: 'merged'`
- Store all three in `transcripts` table

File: `src/transcriber.py` — provider classes:
- `SoferAITranscriber` (new)
- `OpenAIWhisperTranscriber` (fix: save `response.words` with timestamps)
- `AssemblyAITranscriber` (existing)
- `DeepgramTranscriber` (existing)

---

## 7. Phase 2 — Sefaria Integration & Text Alignment <a name="phase-2"></a>

### 2.1 Sefaria MCP Client

File: `src/sefaria_client.py`

- Fetch source units by canonical ref
- Store in `works` + `source_units` tables (cached, `cache_ttl_days`)
- `parse_hierarchy()` — reads Sefaria index to populate `works.level_1_name` etc.

### 2.2 Name Standardization

File: `src/sefaria_name_resolver.py`

Problem: teacher says "Hilchos Shabbos Perek Gimmel Halacha Hey", Sefaria expects "Mishneh Torah, Shabbat 3:5".

Resolution process:
1. Query Sefaria MCP for candidate matches
2. Filter by class's configured `sefaria_ref`
3. Apply sequential context (if last episode ended at chapter 3, next is likely chapter 3 or 4)
4. If still ambiguous: LLM disambiguation with all candidates + context
5. Cache resolved name

### 2.3 4-Pass LLM Alignment

File: `src/text_aligner.py`

**Pass 1 — Header Detection**
- Regex + LLM scan for spoken headers: "הלכה ט", "halacha 9", "פרק ג", etc.
- Support Hebrew letter numerals (א=1, ב=2, ...)
- Record `position` in transcript + timestamp
- Flag discourse markers that indicate digression ("by the way", "let me tell you a story")

**Pass 2 — Gap Detection**
- Compare detected headers against all source units for this class's current coverage range
- Flag missing source units (e.g. headers jump 8→10, so 9 is a gap)
- Distinguish: intentional skip ("we'll skip halacha 6") vs. unannounced gap
- Store `is_intentional_skip: true` on alignment record

**Pass 3 — Content Matching**
- Segment transcript by detected headers
- For each segment: LLM matches to best source unit using semantic similarity
- For cross-references (teacher mentions another halacha for comparison): `is_primary_reference: false`
- Position float: estimate where in the source unit the segment content falls

**Pass 4 — Verification**
- LLM reviews all alignments holistically
- Checks for: sequential plausibility, confidence outliers, inconsistencies
- Returns confidence score per alignment

All prompts in `prompts.yaml`. No prompts hardcoded in Python.

---

## 8. Phase 3 — Artifact Planning <a name="phase-3"></a>

### 3.1 Planning Trigger

Configured per class (`artifact_planning_trigger: auto | manual`). On auto: runs after alignment completes for an episode. On manual: CLI command triggers it.

### 3.2 Planning Process

File: `src/artifact_planner.py`

For each source unit covered by the episode:

1. **Fetch context:**
   - Source unit Hebrew text
   - All class transcripts aligned to this source unit (not just current episode)
   - Existing artifacts for this source unit (across all classes) — shown to planner
   - Context mode: FULL (all raw content) or SYNTHESIZED (see 3.4)

2. **Check for existing base plan:**
   - If base plan exists and `always_override_artifact_plan: false`: present to LLM as starting point
   - If `always_override_artifact_plan: true` for this class: generate fresh plan regardless
   - If no base plan exists: generate fresh base plan

3. **LLM artifact planning prompt** returns JSON manifest:

```json
[
  {
    "artifact_type": "image",
    "subtype": "diagram",
    "priority": 1,
    "position": 0.3,
    "reason": "Measurement concept benefits from visual diagram",
    "prompt_focus": "Visual representation of shiur/measurement units",
    "context_mode": "SYNTHESIZED",
    "notes": "A diagram for measurements already exists from Rabbi Cohen's class; this should be a different approach"
  },
  {
    "artifact_type": "image",
    "subtype": "illustration",
    "priority": 2,
    "position": 0.8,
    "reason": "Spiritual atmosphere of the Shabbat concept",
    "prompt_focus": "Symbolic candles and holiness theme",
    "context_mode": "SYNTHESIZED"
  },
  {
    "artifact_type": "video",
    "subtype": null,
    "priority": 3,
    "position": 0.5,
    "reason": "This concept would benefit from animated explanation",
    "prompt_focus": "Animation of sequential steps",
    "context_mode": "FULL",
    "notes": "Video pipeline not yet implemented — plan only"
  }
]
```

4. **Write to DB:**
   - Base plan: `origin_class_id: null`, `is_override: false`
   - Class override: `origin_class_id: <class_id>`, `is_override: true`
   - Insert `artifacts` records with `status: 'planned'` for each item
   - Items of unimplemented types (video, etc.) get `status: 'planned'` and are logged but not queued for generation

### 3.3 Ordering by Existing Artifacts

The planning prompt explicitly receives a snapshot of existing artifacts for this source unit. The LLM is instructed to:
- Note what types already exist
- Avoid exact duplicates unless the override class has a deliberate reason
- Propose complementary types or different approaches to same type

### 3.4 Context Synthesis

File: `src/context_synthesizer.py`

**FULL mode:** send raw Hebrew text + all aligned transcript segments to the artifact planner / image generator.

**SYNTHESIZED mode (default):**
1. Check `context_syntheses` cache (invalidated if source unit text changes)
2. If cache miss: LLM generates concise synopsis optimized for visual content generation
   - What are the key concepts?
   - What is visually interesting or representable?
   - What should an artist know to represent this faithfully?
3. Cache synthesis per (source_unit, class) pair
4. Subsequent artifacts for same source unit/class reuse cached synthesis

---

## 9. Phase 4 — Image Generation <a name="phase-4"></a>

### 4.1 Image Generation Pipeline

File: `src/image_generator.py`

For each `artifact` with `type: 'image'` and `status: 'ordered'`:

1. Resolve style: randomly select from `styles.enabled` (or use override if set)
2. Determine model: `per_subtype_models[subtype]` or default
3. Build prompt using context (FULL or SYNTHESIZED) + style system prompt
4. Call image model API
5. Upload to `s3://bucket/images/{class_id}/{source_unit_ref}/{artifact_id}_v{n}.png`
6. Create `artifact_versions` record
7. Update `artifacts.status` to `generated`, set `current_version_id`

### 4.2 Prompt Construction

No string concatenation. Structured prompt:

```
[base system prompt from image_system_prompt.yaml]
[style snippet for selected style]

Content context:
[SYNTHESIZED or FULL context for this source unit]

Visual focus for this specific image:
[prompt_focus from artifact plan item]

Image subtype: [subtype]
```

### 4.3 Image Decision (within artifact planning)

The artifact planner (Phase 3) makes all decisions about whether an image is needed, how many, and what type. The image generator only executes what's been planned. This keeps decisions in one place and avoids incoherence.

---

## 10. Phase 5 — Telegram Voting & Edit Workflow <a name="phase-5"></a>

### 5.1 Posting to Voting Group

File: `src/telegram_poster.py`

- Post each `artifact_version` with `status: 'generated'` to the voting group
- Caption includes: source unit ref, subtype, class/teacher, style used
- Record `telegram_message_id` on a new `vote_sessions` record
- Update artifact version status to `in_review`

### 5.2 Voting

File: `src/vote_manager.py`

- Webhook receives reaction updates from Telegram
- Upsert into `votes` table (one vote per user per session)
- Cron job checks for expired voting windows every 10 minutes
- On window close: tally, check approval thresholds, update `vote_sessions.status`
- If approved: update artifact version + artifact status to `approved`
- If rejected: status to `rejected`; artifact `current_version_id` unchanged

### 5.3 Edit Request Handling

File: `src/telegram_edit_handler.py`

When a volunteer replies to a bot message in the voting group:

**Stage 1 — Noise filter (regex/keywords):**
- Short acknowledgements ("thanks", "looks great") → ignore
- Questions about halacha content → ignore
- @mentions without edit intent → ignore

**Stage 2 — LLM classifier:**
Classifies reply as: `style_override | content_edit | ambiguous | noise`

**Stage 3 — Handle by type:**

- `style_override`: extract style name, validate against `styles.enabled`, queue re-generation with that style locked (`style_source: 'telegram_override'`)
- `content_edit`: extract structured edit instructions, send directly to image model with parent image + edit instructions, no prompt rewriting intermediary
- `ambiguous`: bot replies asking for clarification
- `noise`: ignore silently

**All edits produce a new `artifact_versions` record** with `parent_version_id` pointing to the version being edited. The new version goes through full vote process (`status: 'in_review'`, new `vote_sessions` record). Old version status is not changed (history preserved).

**Safeguard against unrelated messages:** Only messages that are direct thread replies to a bot post are eligible for edit processing. Freestanding messages in the group are ignored entirely.

---

## 11. Phase 6 — WhatsApp Distribution <a name="phase-6"></a>

### 6.1 Subscriber Management

File: `src/whatsapp_sender.py`

- `whatsapp_subscribers` table: phone (E.164), name, status, preferences
- Class-level opt-in: `classes.whatsapp_opt_in` in config
- Subscribers receive artifacts only from classes where `whatsapp_opt_in: true`

CLI commands:
```bash
python main.py add-subscriber <phone> [--name <name>]
python main.py remove-subscriber <phone>
python main.py list-subscribers
```

### 6.2 Blast Timing

Configurable per class: `immediate` (queued as soon as artifact approved) or `scheduled` (batched, cron-based). Scheduled timing configured in `config.yaml` per class.

### 6.3 Send & Track

- Rate-limited: `rate_limit_per_second` from config
- Retry on failure: `max_retries`, exponential backoff
- Every send attempt recorded in `whatsapp_deliveries`
- Webhook receives delivery status updates (sent → delivered → read → failed)
- Update `delivery_status` in real-time via `api.py` webhook endpoint

---

## 12. Phase 7 — Artifact Lifecycle Management <a name="phase-7"></a>

### 7.1 Artifact Status Transitions

```
planned
  └─► ordered
        └─► generated
              └─► in_review
                    ├─► approved
                    │     └─► published
                    │           └─► hidden
                    └─► rejected
                          └─► hidden (via reconciliation or manual)
```

`hidden` is reachable from any terminal status. Hidden artifacts are excluded from all delivery queues and frontend displays (future). They remain in the DB for audit/history.

### 7.2 LLM Reconciliation Pass

File: `src/reconciliation.py`

Scheduled cron (configurable frequency). LLM reviews all artifacts for a source unit and flags:

- `stale_superseded`: older version that was never published and a newer version was approved
- `orphaned`: artifact with no current vote session and no published version, idle > N days
- `duplicate_type`: two approved artifacts of identical subtype for same source unit/class
- `never_published`: approved artifact not sent to WhatsApp within N days

Each flag is written to `reconciliation_flags` with LLM recommendation.

### 7.3 Human Approval (Configurable)

If `reconciliation.require_human_approval: true`:
- Flags shown via CLI review command; human confirms or dismisses each
- On confirm: artifact status set to `hidden`

If `require_human_approval: false`:
- LLM recommendation is auto-applied

### 7.4 Manual Override

```bash
# Hide specific artifact version
python main.py hide-artifact-version <version_id> [--reason "..."]

# Restore a previously hidden version as current
python main.py restore-artifact-version <version_id>

# Review reconciliation flags
python main.py review-reconciliation

# Force-publish an artifact (bypass voting — admin only)
python main.py force-publish <artifact_id>
```

---

## 13. Phase 8 — AWS Deployment <a name="phase-8"></a>

### 8.1 Services

| Service | Purpose |
|---|---|
| ECS Fargate (worker) | Main pipeline processor, SQS consumer |
| ECS Fargate (api) | FastAPI webhook server (Telegram, WhatsApp) |
| RDS PostgreSQL | Primary database |
| S3 | Audio, transcripts, images |
| SQS | Job queue (transcription, generation, blast jobs) |
| EventBridge | Cron: vote tally (every 10 min), reconciliation, scheduled blasts |
| Secrets Manager | All API keys |
| CloudWatch | Centralized structured logs + alarms |
| ECR | Docker image registry |

### 8.2 New Files

- `worker.py` — SQS consumer, dispatches to pipeline stages
- `api.py` — FastAPI: `/webhook/telegram`, `/webhook/whatsapp`, `/health`
- `cron_vote_tally.py` — closes expired voting windows, queues blast jobs
- `cron_reconciliation.py` — runs LLM reconciliation pass
- `Dockerfile` — python:3.11-slim, includes ffmpeg
- `docker-compose.yml` — local dev (postgres + worker + api)
- `render.yaml` or `terraform/` — infra as code

### 8.3 Environment Variables (all via Secrets Manager in prod)

```
DATABASE_URL
AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION
S3_BUCKET
SQS_QUEUE_URL
SOFER_AI_API_KEY
OPENAI_API_KEY
ANTHROPIC_API_KEY
REPLICATE_API_TOKEN
TELEGRAM_BOT_TOKEN
TELEGRAM_VOTING_CHAT_ID
WHATSAPP_PHONE_ID / WHATSAPP_ACCESS_TOKEN
```

---

## 14. Logging & Observability <a name="logging"></a>

### Structured Logging Requirements

Every log entry: `timestamp`, `level`, `correlation_id`, `stage`, `class_id`, `episode_id`, `source_unit_ref`, `pipeline_run_id`, `message`, `data`.

Correlation ID generated at pipeline run start, threaded through all async jobs, HTTP calls, and DB operations for that run.

### CloudWatch Alarms

- Alignment confidence average drops below 0.70
- Artifact approval rate drops below 50% (7-day rolling)
- WhatsApp delivery failure rate exceeds 5%
- SQS queue depth exceeds 100 (processing backlog)
- Any pipeline run stuck in `running` for more than 2 hours

### Key Metrics to Track

- Episodes processed / day / class
- Average alignment confidence per class
- Artifact approval rate per class
- Images generated vs. planned (ratio)
- WhatsApp delivery success rate
- Cost per episode (S3 + LLM + image model API calls)
- Pipeline run duration per stage

---

## 15. Out of Scope / Future Phases <a name="future"></a>

These are explicitly deferred. Artifact types are registered in the DB but pipelines are not built.

- **Video pipeline** — `artifact_types` row exists with `is_implemented: false`
- **Interactive chart/graph pipeline** — same
- **Text snippet pipeline** — same
- **Weighted chapter images** (based on time-spent per chapter) — deferred
- **Reputation/weighted voting** — not needed with current volunteer count
- **Multi-language support** (English classes, English Sefaria text)
- **Frontend UI** — artifact lifecycle management currently CLI-only; `hidden` status and reconciliation tooling is designed with frontend in mind
- **Cross-class image reuse suggestions** — planner sees existing artifacts but does not yet auto-reuse them

---

## 16. Open Questions <a name="open-questions"></a>

These require decisions before or during implementation:

1. **`chapters` table in existing codebase** — confirmed: clean slate, no migration needed. Ignore existing table naming.

2. **Artifact position float precision** — 0.0–1.0 is defined but the exact derivation method (from timestamp ratio within alignment window, or LLM estimate) is TBD during Phase 3 implementation.

3. **Scheduled WhatsApp blast timing** — `scheduled` option is configurable per class but the specific schedule format (cron expression? fixed daily time? configurable per class?) is TBD.

4. **Telegram bot setup** — one bot for all classes confirmed, but bot configuration (commands list, group permissions) is outside scope of this plan.

5. **Sefaria MCP authentication** — public API is unauthenticated but rate-limited; MCP access details to be confirmed during Phase 2.

---

## File Index — New Files to Create

```
src/
  db.py                       # PostgreSQL connection + pooling
  storage.py                  # S3 abstraction
  queue.py                    # SQS job queue
  config.py                   # Config loader with per-class override merging
  logger.py                   # Structured JSON logger + correlation IDs
  rss_parser.py               # Refactor: multi-class support
  dual_transcriber.py         # Parallel transcription + merge
  transcriber.py              # Add SoferAITranscriber, fix Whisper timestamps
  sefaria_client.py           # Sefaria API + MCP
  sefaria_name_resolver.py    # Canonical name resolution + disambiguation
  text_aligner.py             # 4-pass LLM alignment
  artifact_planner.py         # LLM artifact planning pass
  context_synthesizer.py      # FULL/SYNTHESIZED context modes
  image_generator.py          # Image generation + style rotation
  telegram_poster.py          # Post to voting group
  telegram_edit_handler.py    # Edit request validation + dispatch
  vote_manager.py             # Voting logic + tally
  whatsapp_sender.py          # WhatsApp Business API + blast
  reconciliation.py           # LLM reconciliation pass
  pipeline.py                 # Main orchestrator (refactor)

worker.py                     # SQS consumer
api.py                        # FastAPI webhooks
cron_vote_tally.py            # Close expired votes
cron_reconciliation.py        # Run reconciliation pass
main.py                       # CLI (refactor + new commands)

prompts/
  image_system_prompt.yaml    # Style presets + base system prompt
  alignment_prompts.yaml      # 4-pass alignment prompts
  artifact_planning.yaml      # Artifact planner prompt
  edit_classifier.yaml        # Telegram edit request classifier prompt
  reconciliation.yaml         # Reconciliation pass prompt
  context_synthesis.yaml      # Synthesis prompt

migrations/
  001_works_source_units.sql
  002_classes_episodes.sql
  003_transcripts_alignments.sql
  004_artifact_types_plans.sql
  005_artifacts_versions.sql
  006_pipeline_runs.sql
  007_voting.sql
  008_whatsapp.sql
  009_reconciliation.sql
  010_context_syntheses.sql

terraform/
  main.tf
  rds.tf
  ecs.tf
  iam.tf
  eventbridge.tf
  variables.tf
  outputs.tf

Dockerfile
docker-compose.yml
.env.example
```
