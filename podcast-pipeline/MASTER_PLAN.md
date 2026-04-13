# 🎯 Comprehensive Implementation Plan

## Overview

This plan outlines the implementation of a Hebrew podcast processing pipeline with:
- sofer.ai Hebrew transcription + dual transcription for timestamps
- Sefaria API integration for source text alignment
- LLM-based transcript-to-text alignment (4-pass system)
- Telegram voting system with reaction-based approval
- WhatsApp Business API blasting to subscribers
- AWS cloud deployment (ECS, RDS, S3, SQS)

---

## Phase 1: Core Infrastructure & Database Migration

### Step 1.1: PostgreSQL Migration

**Files to modify/create:**
- `src/state.py` - Update for PostgreSQL
- `migrations/001_initial_schema.sql` - Base schema
- `migrations/002_add_text_alignment.sql` - Text/alignment tables
- `migrations/003_add_voting.sql` - Voting tables
- `migrations/004_add_whatsapp.sql` - WhatsApp tables
- `src/db.py` - Database connection manager

**New schema additions:**

```sql
-- Original text storage
CREATE TABLE source_texts (
    id SERIAL PRIMARY KEY,
    ref TEXT UNIQUE NOT NULL,  -- e.g., "Mishneh Torah, Shabbat 1:1"
    hebrew_text TEXT NOT NULL,
    structure JSONB,  -- {book, chapter, halacha}
    fetched_at TIMESTAMP DEFAULT NOW()
);

-- Text alignment
CREATE TABLE text_alignments (
    id SERIAL PRIMARY KEY,
    episode_guid TEXT REFERENCES episodes(guid),
    chapter_id INTEGER REFERENCES chapters(id),
    source_text_id INTEGER REFERENCES source_texts(id),
    transcript_start_ms INTEGER,
    transcript_end_ms INTEGER,
    confidence_score FLOAT,
    alignment_method TEXT,  -- 'header_detection', 'content_match', 'manual'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Telegram voting
CREATE TABLE telegram_votes (
    id SERIAL PRIMARY KEY,
    telegram_message_id BIGINT NOT NULL,
    chapter_id INTEGER REFERENCES chapters(id),
    user_id BIGINT NOT NULL,
    username TEXT,
    vote_type TEXT CHECK (vote_type IN ('upvote', 'downvote')),
    voted_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(telegram_message_id, user_id)
);

CREATE TABLE asset_approvals (
    id SERIAL PRIMARY KEY,
    chapter_id INTEGER UNIQUE REFERENCES chapters(id),
    telegram_message_id BIGINT,
    voting_opened_at TIMESTAMP,
    voting_closed_at TIMESTAMP,
    upvotes_count INTEGER DEFAULT 0,
    downvotes_count INTEGER DEFAULT 0,
    approval_percentage FLOAT,
    status TEXT DEFAULT 'pending',  -- pending, approved, rejected, published
    approved_at TIMESTAMP
);

-- WhatsApp subscribers
CREATE TABLE whatsapp_subscribers (
    phone_number TEXT PRIMARY KEY,
    name TEXT,
    subscribed_at TIMESTAMP DEFAULT NOW(),
    status TEXT DEFAULT 'active',  -- active, inactive, blocked
    preferences JSONB DEFAULT '{}'
);

CREATE TABLE whatsapp_deliveries (
    id SERIAL PRIMARY KEY,
    chapter_id INTEGER REFERENCES chapters(id),
    subscriber_phone TEXT REFERENCES whatsapp_subscribers(phone_number),
    whatsapp_message_id TEXT,
    sent_at TIMESTAMP,
    delivery_status TEXT,  -- queued, sent, delivered, read, failed
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

-- Dual transcription storage
ALTER TABLE episodes ADD COLUMN primary_transcript_path TEXT;
ALTER TABLE episodes ADD COLUMN timestamped_transcript_path TEXT;
ALTER TABLE episodes ADD COLUMN merged_transcript_path TEXT;
```

### Step 1.2: AWS S3 Storage Layer

**Files to create:**
- `src/storage.py`

**Key functionality:**
- Upload files to S3
- Generate public URLs
- Download files from S3
- Abstraction layer for easy provider switching

### Step 1.3: SQS Job Queue

**Files to create:**
- `src/queue.py`

**Key functionality:**
- Send jobs to SQS queue
- Receive jobs with long polling
- Delete processed jobs
- Process jobs with handlers

---

## Phase 2: Transcription Enhancements

### Step 2.1: sofer.ai Integration

**Files to modify:**
- `src/transcriber.py` - Add `SoferAITranscriber` class

**Implementation:**
- Upload audio to sofer.ai API
- Poll for completion
- Parse Hebrew transcription results
- Cache results to avoid re-transcription
- No timestamps (accurate Hebrew text only)

**Update factory function:**
```python
def get_transcriber(cfg: dict):
    provider = cfg['transcription']['provider']
    
    if provider == 'sofer_ai':
        return SoferAITranscriber(cfg)
    # ... existing providers
```

### Step 2.2: Dual Transcription System

**Files to create:**
- `src/dual_transcriber.py`

**Key functionality:**
- Run two transcriptions in parallel:
  - Primary: sofer.ai (accurate Hebrew, no timestamps)
  - Secondary: Whisper/AssemblyAI (timestamps)
- Merge results using word alignment
- Use difflib SequenceMatcher for alignment
- Return merged TranscriptResult with accurate text + timestamps

### Step 2.3: Fix Whisper Timestamps

**Files to modify:**
- `src/transcriber.py` - Update `OpenAIWhisperTranscriber`

**Changes:**
- Save `response.words` array (currently only saves text)
- Convert timestamps to milliseconds
- Store in `TranscriptResult.words` field
- Each word has: `word`, `start`, `end`

---

## Phase 3: Sefaria Integration & Text Alignment

### Step 3.1: Sefaria API Client

**Files to create:**
- `src/sefaria_client.py`

**Key functionality:**
- Fetch Hebrew texts from Sefaria API
- Support for Rambam (Mishneh Torah) structure
- Parse book/chapter/halacha structure
- Fetch ranges of halachot
- Extract only Hebrew text (no translations)

**Example usage:**
```python
client = SefariaClient()
data = client.fetch_text("Mishneh Torah, Shabbat 1:1-10")
halachot = client.parse_structure(data)
```

### Step 3.2: Text Alignment Engine

**Files to create:**
- `src/text_aligner.py`

**4-Pass Alignment System:**

#### Pass 1: Header Detection
- Find spoken halacha headers in transcript
- Patterns: "halacha 9", "halacha ט", "הלכה ט"
- Support Hebrew and English numbers
- Extract timestamps for each halacha header
- Hebrew number mapping: א=1, ב=2, ג=3, etc.

#### Pass 2: Gap Detection
- Compare detected halacha headers to source text
- Find missing halachot (e.g., 8 → 10, missing 9)
- Identify surrounding halachot for context
- Prepare for content-based inference

#### Pass 3: Content Matching (LLM)
- Split transcript into segments based on halacha headers
- Use LLM to match segments to source halachot
- Semantic content matching
- Return confidence scores
- Handle gaps using content similarity

#### Pass 4: Verification (LLM)
- Verify each alignment
- LLM checks if transcript matches source halacha
- Approve/reject alignments
- Suggest adjustments to boundaries
- Final confidence scoring

**Output:**
```python
[{
    'transcript_segment': {...},
    'source_ref': 'Mishneh Torah, Shabbat 1:5',
    'chapter_num': 1,
    'halacha_num': 5,
    'start_ms': 12000,
    'end_ms': 45000,
    'confidence': 0.95,
    'verified': True
}]
```

---

## Phase 4: Telegram Voting System

### Step 4.1: Enhanced Telegram Poster with Voting

**Files to modify:**
- `src/telegram_poster.py`

**New functionality:**
- `post_for_voting()` method
- Post to separate voting group
- Format caption with voting instructions
- Include chapter metadata
- Display voting window duration
- Users react with 👍 or 👎

### Step 4.2: Vote Manager

**Files to create:**
- `src/vote_manager.py`

**Key functionality:**
- `tally_votes()` - Count upvotes/downvotes
- `check_approval()` - Check if meets criteria
- `close_voting()` - Close window and determine status
- `get_expired_votes()` - Find expired voting windows

**Approval logic:**
- Configurable minimum approval percentage (e.g., 70%)
- Configurable minimum total votes (e.g., 3)
- Option to require both criteria or either

---

## Phase 5: WhatsApp Integration

### Step 5.1: WhatsApp Sender

**Files to create:**
- `src/whatsapp_sender.py`

**Key functionality:**
- Send image + caption via WhatsApp Business API
- Get active subscribers from database
- Blast to all subscribers with rate limiting
- Track delivery status
- Handle errors and retries
- Record deliveries in database

**Rate limiting:**
- Configurable messages per second (default: 20)
- Delay between messages to avoid API limits

**Delivery tracking:**
- Record sent_at timestamp
- Track delivery status (sent/delivered/read/failed)
- Store WhatsApp message ID
- Log errors for failed deliveries

---

## Phase 6: AWS Deployment Files

### Step 6.1: Worker Process

**Files to create:**
- `worker.py`

**Functionality:**
- SQS job consumer
- Process episode jobs (full pipeline)
- Process WhatsApp blast jobs
- Continuous polling with long wait times
- Error handling and logging

**Job handlers:**
- `process_episode` - Run full pipeline for episode
- `whatsapp_blast` - Send approved chapter to subscribers

### Step 6.2: Webhook API

**Files to create:**
- `api.py`

**FastAPI endpoints:**
- `POST /webhook/telegram` - Handle Telegram reactions
- `POST /webhook/whatsapp` - Handle WhatsApp delivery status
- `GET /health` - Health check

**Telegram webhook:**
- Receive message_reaction updates
- Parse emoji (👍 = upvote, 👎 = downvote)
- Store vote in database
- Update existing votes if user changes reaction

**WhatsApp webhook:**
- Receive delivery status updates
- Update delivery records in database
- Track: sent, delivered, read, failed

### Step 6.3: Cron Job

**Files to create:**
- `cron_vote_tally.py`

**Functionality:**
- Run every 10 minutes (EventBridge schedule)
- Find expired voting windows
- Close voting and tally results
- Update approval status
- Queue approved chapters for WhatsApp blast

---

## Phase 7: Configuration Updates

### Step 7.1: Update config.yaml

**New sections to add:**

```yaml
# AWS Configuration
aws:
  region: "us-east-1"
  s3_bucket: "podcast-pipeline-assets"
  sqs_queue_url: "https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/podcast-pipeline-jobs"

# Dual Transcription
transcription:
  primary_provider: "sofer_ai"  # Accurate Hebrew
  timestamp_provider: "openai_whisper"  # For timestamps
  
  sofer_ai:
    language: "he"
    model: "default"
    base_url: "https://api.sofer.ai/v1"

# Text Alignment
text_alignment:
  llm:
    provider: "anthropic"
    model: "claude-sonnet-4-20250514"
  source: "sefaria"
  default_book: "Mishneh Torah, Shabbat"

# Sefaria
sefaria:
  base_url: "https://www.sefaria.org/api"
  language: "he"

# Telegram Voting
telegram:
  voting_group_chat_id: "-1001234567890"
  upvote_emoji: "👍"
  downvote_emoji: "👎"
  voting_window_hours: 24

# Approval Criteria
approval:
  min_approval_percentage: 70
  min_total_votes: 3
  require_both_criteria: true

# WhatsApp
whatsapp:
  rate_limit_messages_per_second: 20
  retry_failed_deliveries: true
  max_retries: 3
```

### Step 7.2: Update prompts.yaml

**New prompts to add:**

```yaml
text_alignment:
  content_match: |
    You are aligning a podcast transcript to the original Hebrew text of Rambam.
    
    Transcript segment:
    {transcript_segment}
    
    Available source texts:
    {source_texts}
    
    Detected halacha number: {detected_halacha}
    
    Return JSON with the best matching source text:
    {{
      "ref": "Mishneh Torah, Shabbat 1:5",
      "halacha_num": 5,
      "confidence": 0.95,
      "reasoning": "..."
    }}
  
  verify: |
    Verify this alignment between transcript and source text.
    
    Transcript: {transcript_text}
    Source: {source_text}
    Confidence: {confidence}
    
    Return JSON:
    {{
      "approved": true/false,
      "reason": "...",
      "adjustments": {{"start_offset": 0, "end_offset": 0}}
    }}
```

### Step 7.3: Update .env.example

**New environment variables:**

```bash
# AWS
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1

# sofer.ai
SOFER_AI_API_KEY=your_sofer_ai_key

# WhatsApp Business
WHATSAPP_PHONE_ID=your_phone_id
WHATSAPP_ACCESS_TOKEN=your_access_token
```

---

## Phase 8: Updated Pipeline Flow

### Step 8.1: Modify main pipeline

**Files to modify:**
- `src/pipeline.py`

**New imports:**
```python
from .dual_transcriber import DualTranscriber
from .sefaria_client import SefariaClient
from .text_aligner import TextAligner
from .vote_manager import VoteManager
from .storage import get_storage
```

**Updated flow in `_process_episode()`:**

1. Download audio (existing)
2. **Dual transcription** (new)
   - Run sofer.ai + Whisper in parallel
   - Merge results with word alignment
3. **Fetch Sefaria text** (new)
   - Get Hebrew source text
   - Store in source_texts table
4. **Align transcript to source** (new)
   - 4-pass alignment process
   - Store alignments in database
5. **LLM decides images per halacha** (new) - 0 to N images per halacha
6. Generate decided images (existing)
7. **Upload to S3** (new)
8. **Post to Telegram voting group** (new)
9. **Record in approvals table** (new)

---

## Phase 9: Deployment

### Step 9.1: Terraform Infrastructure

**Files to create:**
- `terraform/main.tf` - Main resources
- `terraform/variables.tf` - Input variables
- `terraform/outputs.tf` - Output values
- `terraform/rds.tf` - PostgreSQL database
- `terraform/s3.tf` - Storage buckets
- `terraform/ecs.tf` - Container services
- `terraform/sqs.tf` - Job queues
- `terraform/secrets.tf` - Secrets Manager
- `terraform/iam.tf` - Permissions

**Resources to create:**
- S3 bucket for assets (audio, transcripts, images)
- RDS PostgreSQL (db.t3.micro for dev)
- SQS queue for jobs
- ECS Fargate cluster
- ECS task definitions (worker, api)
- ECR repository for Docker images
- Secrets Manager for API keys
- CloudWatch log groups
- EventBridge rules for cron jobs
- IAM roles and policies

### Step 9.2: Docker Configuration

**Files to create:**
- `Dockerfile` - Container definition
- `docker-compose.yml` - Local development
- `.dockerignore` - Exclude files from build
- `buildspec.yml` - AWS CodeBuild CI/CD

**Dockerfile highlights:**
- Python 3.11 slim base
- Install ffmpeg for audio processing
- Install dependencies
- Copy application code
- Configurable CMD (override in ECS)

**docker-compose.yml:**
- PostgreSQL service
- Worker service
- API service
- Shared volumes for development

### Step 9.3: CI/CD Pipeline

**Files to create:**
- `.github/workflows/deploy.yml` - GitHub Actions (optional)
- `buildspec.yml` - AWS CodeBuild

**Deployment flow:**
1. Push to main branch
2. Build Docker image
3. Push to ECR
4. Update ECS task definition
5. Deploy to ECS services

---

## Phase 10: CLI Updates

### Step 10.1: Add new commands

**Files to modify:**
- `main.py`

**New commands:**

```bash
# Check voting status
python main.py voting-status

# Manually approve/reject asset
python main.py approve <chapter_id>
python main.py reject <chapter_id>

# Close voting early
python main.py close-voting <chapter_id>

# Send to WhatsApp (approved assets)
python main.py send-whatsapp

# Manage subscribers
python main.py add-subscriber <phone_number> --name "Name"
python main.py remove-subscriber <phone_number>
python main.py list-subscribers

# Test alignment
python main.py test-alignment <episode_guid>

# Fetch Sefaria text
python main.py fetch-sefaria "Mishneh Torah, Shabbat 1"
```

---

## Complete End-to-End Flow

### 1. Audio Processing
- Download audio from RSS feed
- Upload to S3 for storage

### 2. Dual Transcription
- sofer.ai: Accurate Hebrew transcription
- Whisper: Timestamped transcription
- Merge: Accurate text + timestamps

### 3. Source Text Retrieval
- Fetch Hebrew text from Sefaria API
- Parse Rambam structure (book/chapter/halacha)
- Store in database

### 4. Text Alignment (4 Passes)
- Pass 1: Detect spoken halacha headers
- Pass 2: Find gaps in halacha coverage
- Pass 3: Match content with LLM
- Pass 4: Verify alignments with LLM

### 5. Image Decision & Generation (Per Halacha)
- LLM analyzes each halacha
- Decides: 0, 1, 2, or 3 images needed
- Decides: image type (illustration, diagram, infographic, etc.)
- Generate decided images
- Upload to S3
- Store public URL

### 7. Telegram Voting
- Post to voting group
- Users react with 👍 or 👎
- Voting window (24 hours default)

### 8. Vote Tallying (Cron)
- Every 10 minutes, check for expired votes
- Tally upvotes/downvotes
- Check approval criteria
- Update status (approved/rejected)

### 9. WhatsApp Blasting
- Queue approved chapters
- Send to all active subscribers
- Rate-limited delivery
- Track delivery status

### 10. Delivery Tracking
- Webhook receives status updates
- Update database records
- Monitor success/failure rates

---

## AWS Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         AWS Cloud                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │ EventBridge  │────────▶│ ECS Fargate  │                  │
│  │   (Cron)     │         │   Worker     │                  │
│  └──────────────┘         └──────┬───────┘                  │
│                                   │                          │
│  ┌──────────────┐         ┌──────▼───────┐                  │
│  │ API Gateway  │────────▶│     SQS      │                  │
│  │  (Webhooks)  │         │  Job Queue   │                  │
│  └──────┬───────┘         └──────────────┘                  │
│         │                                                    │
│  ┌──────▼───────┐         ┌──────────────┐                  │
│  │   Lambda     │────────▶│     RDS      │                  │
│  │  Functions   │         │  PostgreSQL  │                  │
│  └──────────────┘         └──────────────┘                  │
│                                   │                          │
│  ┌──────────────┐         ┌──────▼───────┐                  │
│  │      S3      │◀────────│ ECS Fargate  │                  │
│  │   Storage    │         │  API Service │                  │
│  └──────────────┘         └──────────────┘                  │
│                                   │                          │
│  ┌──────────────┐         ┌──────▼───────┐                  │
│  │   Secrets    │◀────────│  CloudWatch  │                  │
│  │   Manager    │         │   Logs       │                  │
│  └──────────────┘         └──────────────┘                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
         │                           │
         ▼                           ▼
   External APIs:          Message Delivery:
   - sofer.ai              - Telegram
   - Sefaria               - WhatsApp Business
   - OpenAI Whisper        
   - Anthropic Claude
   - Replicate (Flux)
```

---

## Summary: Files to Create/Modify

### New Files (30+):

**Core Application:**
1. `src/storage.py` - S3 abstraction
2. `src/queue.py` - SQS job queue
3. `src/dual_transcriber.py` - Dual transcription
4. `src/sefaria_client.py` - Sefaria API
5. `src/text_aligner.py` - LLM alignment
6. `src/vote_manager.py` - Voting logic
7. `src/whatsapp_sender.py` - WhatsApp API
8. `src/db.py` - DB connection manager

**Services:**
9. `worker.py` - Background worker
10. `api.py` - Webhook server
11. `cron_vote_tally.py` - Cron job

**Database:**
12. `migrations/001_initial_schema.sql`
13. `migrations/002_add_text_alignment.sql`
14. `migrations/003_add_voting.sql`
15. `migrations/004_add_whatsapp.sql`

**Infrastructure:**
16. `terraform/main.tf`
17. `terraform/variables.tf`
18. `terraform/outputs.tf`
19. `terraform/rds.tf`
20. `terraform/s3.tf`
21. `terraform/ecs.tf`
22. `terraform/sqs.tf`
23. `terraform/secrets.tf`
24. `terraform/iam.tf`

**Deployment:**
25. `Dockerfile`
26. `docker-compose.yml`
27. `buildspec.yml`
28. `.dockerignore`
29. `.github/workflows/deploy.yml` (optional)
30. `requirements-aws.txt`

### Modified Files (7):

1. `src/transcriber.py` - Add sofer.ai, fix Whisper timestamps
2. `src/telegram_poster.py` - Add voting posts
3. `src/pipeline.py` - Integrate all new features
4. `src/state.py` - PostgreSQL support
5. `config.yaml` - Add all new config sections
6. `prompts.yaml` - Add alignment prompts
7. `main.py` - Add new CLI commands

---

## Implementation Order

### Week 1: Foundation
1. PostgreSQL migration (Phase 1.1)
2. S3 storage layer (Phase 1.2)
3. SQS job queue (Phase 1.3)

### Week 2: Transcription
4. sofer.ai integration (Phase 2.1)
5. Dual transcription system (Phase 2.2)
6. Fix Whisper timestamps (Phase 2.3)

### Week 3: Text Alignment
7. Sefaria API client (Phase 3.1)
8. Text alignment engine (Phase 3.2)
9. Test alignment with sample data

### Week 4: Voting & WhatsApp
10. Telegram voting system (Phase 4)
11. WhatsApp integration (Phase 5)
12. Vote manager and cron job

### Week 5: AWS Deployment
13. Docker configuration (Phase 9.2)
14. Terraform infrastructure (Phase 9.1)
15. Deploy to AWS

### Week 6: Testing & Polish
16. End-to-end testing
17. CLI updates (Phase 10)
18. Documentation
19. Monitoring and alerts

---

## Cost Estimates (AWS)

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| ECS Fargate | 2 tasks (0.5 vCPU, 1GB RAM) | $30-40 |
| RDS PostgreSQL | db.t3.micro | $15-20 |
| S3 | 100GB storage + requests | $5-10 |
| SQS | 1M requests | $0.40 |
| EventBridge | Cron jobs | Free tier |
| Secrets Manager | 5 secrets | $2 |
| CloudWatch | Logs + metrics | $5-10 |
| Data Transfer | Outbound | $5-10 |
| **Total** | | **~$65-95/month** |

---

## Testing Strategy

### Unit Tests
- Test each module independently
- Mock external APIs (sofer.ai, Sefaria, WhatsApp)
- Test alignment algorithms with sample data

### Integration Tests
- Test full pipeline with sample episode
- Test dual transcription merge
- Test voting workflow
- Test WhatsApp delivery

### End-to-End Tests
- Process real podcast episode
- Verify all data stored correctly
- Check S3 uploads
- Verify Telegram posts
- Test approval workflow

---

## Monitoring & Alerts

### CloudWatch Metrics
- Job processing time
- Transcription success/failure rate
- Alignment confidence scores
- Voting participation rate
- WhatsApp delivery success rate

### Alerts
- Failed transcriptions
- Low alignment confidence
- WhatsApp API errors
- Database connection issues
- SQS queue depth

---

## Security Considerations

1. **API Keys**: Store in AWS Secrets Manager
2. **Database**: Use IAM authentication, encrypt at rest
3. **S3**: Enable encryption, use signed URLs if needed
4. **Webhooks**: Verify signatures from Telegram/WhatsApp
5. **Network**: Use VPC, security groups, private subnets
6. **Logging**: Sanitize PII from logs

---

## Future Enhancements

1. **Multi-teacher support**: Track which teacher covers which halachot
2. **Video generation**: Use timestamps to create video overlays
3. **Analytics dashboard**: Track engagement, popular topics
4. **A/B testing**: Test different image styles
5. **Subscriber preferences**: Allow topic/frequency selection
6. **Multi-language**: Support other languages beyond Hebrew
7. **Audio enhancement**: Noise reduction, normalization
8. **Speaker diarization**: Identify different speakers
9. **Search**: Full-text search across transcripts
10. **API**: Public API for accessing processed content

---

## Questions & Decisions Needed

1. **sofer.ai API**: Confirm API endpoints and authentication
2. **WhatsApp Business**: Confirm account setup and phone number
3. **Telegram Bot**: Create bot and get voting group ID
4. **AWS Account**: Confirm account and region
5. **Sefaria**: Confirm API rate limits
6. **Image Style**: Finalize Flux model and prompts
7. **Voting Window**: Confirm 24 hours is appropriate
8. **Approval Threshold**: Confirm 70% and 3 votes minimum
9. **Subscriber Management**: How do users subscribe/unsubscribe?
10. **Content Moderation**: Any additional review before WhatsApp?

---

## Success Metrics

1. **Transcription Accuracy**: >95% for Hebrew text
2. **Alignment Confidence**: >90% average confidence score
3. **Voting Participation**: >50% of volunteers vote
4. **Approval Rate**: 60-80% of assets approved
5. **WhatsApp Delivery**: >95% successful delivery
6. **Processing Time**: <30 minutes per episode
7. **Cost per Episode**: <$5 per episode processed
8. **Uptime**: >99% availability

---

## Support & Maintenance

### Daily
- Monitor CloudWatch logs
- Check failed jobs
- Review voting results

### Weekly
- Review alignment quality
- Check subscriber growth
- Analyze engagement metrics

### Monthly
- Review AWS costs
- Update dependencies
- Backup database
- Review and improve prompts

---

## Documentation

### User Documentation
- How to subscribe/unsubscribe (WhatsApp)
- How to vote (Telegram)
- FAQ

### Developer Documentation
- Setup instructions
- API documentation
- Architecture diagrams
- Deployment guide

### Operations Documentation
- Runbook for common issues
- Monitoring guide
- Backup/restore procedures
- Scaling guide

---

## Conclusion

This implementation plan provides a comprehensive roadmap for building a production-grade Hebrew podcast processing pipeline with advanced features including dual transcription, LLM-based text alignment, community voting, and automated WhatsApp distribution.

The system is designed to be:
- **Scalable**: AWS infrastructure can handle growth
- **Reliable**: Error handling, retries, monitoring
- **Maintainable**: Modular architecture, clear separation of concerns
- **Cost-effective**: Optimized resource usage
- **Extensible**: Easy to add new features

Estimated timeline: 6 weeks for full implementation and testing.
# 🔍 Codebase Analysis & Required Changes

## Executive Summary

After reviewing the codebase with the new requirements, several major architectural changes are needed:

1. **Multi-RSS Feed Support** - Current system only handles one feed at a time
2. **Class-to-Chapter Tracking** - Need to track which Rambam chapters each class covers
3. **Chapter Name Standardization** - LLM normalization of chapter names to Sefaria format
4. **Telegram Edit Workflow** - Interactive image editing via replies
5. **Image Versioning** - Track multiple versions of images with lineage
6. **Chapter Splitting Strategy** - Current "both" strategy conflicts with new alignment approach

---

## Critical Issues Found

### 1. Terminology Confusion: Halacha ≠ Chapter ⚠️

**CRITICAL ERROR IN DOCUMENTATION:**
- A **halacha** is a numbered law within a chapter (e.g., Shabbat 1:5 = Chapter 1, Halacha 5)
- A **chapter** (perek) contains multiple halachot (e.g., Chapter 1 has halachot 1-20)
- Throughout this doc, "chapter splitting" incorrectly conflates these concepts

**Current Implementation Problem:**
```yaml
chapters:
  strategy: "both"  # provider first, fallback to llm
```

**Problem:**
- The current "chapter splitter" uses transcription provider auto-chapters (AssemblyAI)
- This is designed for English podcasts with natural topic breaks
- **Has nothing to do with Rambam structure** (chapters and halachot)
- The "both" strategy will try to use AssemblyAI first, which is completely wrong

**Solution:**
- **Remove the concept of "chapter splitting" entirely**
- Replace with **halacha-level alignment** to Sefaria
- Alignment determines which halachot are covered (e.g., Shabbat 2:5-8, then 3:1-4)
- Images are generated **per halacha** (LLM decides 0-N images per halacha)
- NOT "one image per chapter"

**Required Changes:**
- Deprecate `chapter_splitter.py` entirely for Rambam content
- Use `text_aligner.py` to map transcript → halachot
- Image generation works at halacha granularity

---

### 2. Single RSS Feed Limitation ⚠️

**Current Implementation:**
```python
# rss_parser.py
def fetch_episodes(self, feed_url: str | None = None) -> list[Episode]:
    url = feed_url or self.rss_cfg["feed_url"]
```

**Problem:**
- Only processes one RSS feed per run
- No concept of "classes" (multiple teachers/feeds)
- No tracking of which class an episode belongs to
- No way to compare coverage across different teachers

**Solution:**
- Add `classes` table to database
- Support multiple RSS feeds in config
- Track class_id for each episode
- Add class metadata (teacher name, schedule, etc.)

**Database Schema Addition:**
```sql
CREATE TABLE classes (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    teacher_name TEXT,
    rss_feed_url TEXT UNIQUE NOT NULL,
    sefaria_book_ref TEXT,  -- e.g., "Mishneh Torah, Shabbat"
    current_chapter INT,
    current_halacha INT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE episodes ADD COLUMN class_id INTEGER REFERENCES classes(id);
```

**Config Changes:**
```yaml
# OLD:
rss:
  feed_url: "https://feeds.example.com/mypodcast.rss"

# NEW:
classes:
  - name: "Rabbi Cohen - Hilchot Shabbat"
    teacher: "Rabbi Cohen"
    rss_feed_url: "https://feeds.example.com/cohen-shabbat.rss"
    sefaria_ref: "Mishneh Torah, Shabbat"
    
  - name: "Rabbi Levy - Hilchot Shabbat"
    teacher: "Rabbi Levy"
    rss_feed_url: "https://feeds.example.com/levy-shabbat.rss"
    sefaria_ref: "Mishneh Torah, Shabbat"
```

---

### 3. No Halacha Coverage Tracking ⚠️

**Current Implementation:**
- No tracking of which halachot are covered
- No way to know "Rabbi Cohen is on Chapter 3, Halacha 5"
- No cross-class comparison

**Solution:**
- Add `class_progress` table
- Track halacha coverage per class (which halachot covered in which episodes)
- Update progress after each episode alignment

**Database Schema Addition:**
```sql
CREATE TABLE class_progress (
    id SERIAL PRIMARY KEY,
    class_id INTEGER REFERENCES classes(id),
    episode_guid TEXT REFERENCES episodes(guid),
    chapter_num INTEGER NOT NULL,
    halacha_num INTEGER NOT NULL,
    coverage_start_ms INTEGER,  -- timestamp in episode
    coverage_end_ms INTEGER,
    alignment_confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(class_id, episode_guid, chapter_num, halacha_num)
);

-- View to see current position per class
CREATE VIEW class_current_position AS
SELECT 
    c.id,
    c.name,
    c.teacher_name,
    MAX(cp.chapter_num) as current_chapter,
    MAX(cp.halacha_num) FILTER (WHERE cp.chapter_num = MAX(cp.chapter_num)) as current_halacha
FROM classes c
LEFT JOIN class_progress cp ON c.id = cp.class_id
GROUP BY c.id, c.name, c.teacher_name;
```

---

### 4. No Rambam Reference Standardization ⚠️

**Current Implementation:**
- No normalization to Sefaria format
- Teacher might say "Shabbos" vs "Shabbat", "Hilchos" vs "Hilchot", "Perek Gimmel" vs "Chapter 3"

**Problem:**
- Inconsistent naming across classes
- Can't easily match to Sefaria references
- Hard to compare coverage

**Solution:**
- Add LLM pass to standardize Rambam references
- Map detected names to canonical Sefaria format (e.g., "Mishneh Torah, Shabbat 3:5")
- Store both original and standardized names

**Implementation:**
```python
class SefariaRefStandardizer:
    def standardize(self, detected_ref: str, context: str) -> dict:
        """
        Use LLM to map detected reference to Sefaria format
        
        Input: "Hilchos Shabbos Perek Gimmel Halacha Hey"
        Output: {
            "original": "Hilchos Shabbos Perek Gimmel Halacha Hey",
            "standardized": "Mishneh Torah, Shabbat 3:5",
            "sefaria_ref": "Mishneh Torah, Shabbat 3:5",
            "chapter": 3,
            "halacha": 5,
            "confidence": 0.95
        }
        """
```

**Database Schema Addition:**
```sql
ALTER TABLE text_alignments ADD COLUMN original_spoken_ref TEXT;
ALTER TABLE text_alignments ADD COLUMN standardized_sefaria_ref TEXT;
ALTER TABLE text_alignments ADD COLUMN ref_standardization_confidence FLOAT;
```

---

### 5. No Telegram Edit Workflow ⚠️

**Current Implementation:**
- Images posted to Telegram for voting
- No way to request edits
- No conversation with image model

**Problem:**
- Volunteers can't provide feedback
- No iterative improvement
- Manual regeneration required

**Solution:**
- Monitor Telegram for replies to image messages
- Parse edit requests from volunteers
- Send edit request directly to image model
- Generate new version and post as reply
- Track image versions and lineage

**Database Schema Addition:**
```sql
CREATE TABLE image_versions (
    id SERIAL PRIMARY KEY,
    chapter_id INTEGER REFERENCES chapters(id),
    version_number INTEGER NOT NULL,
    parent_version_id INTEGER REFERENCES image_versions(id),
    image_path TEXT NOT NULL,
    s3_url TEXT,
    telegram_message_id BIGINT,
    generation_prompt TEXT,
    edit_request TEXT,  -- What volunteer asked for
    generated_at TIMESTAMP DEFAULT NOW(),
    status TEXT DEFAULT 'pending',  -- pending, active, superseded, rejected
    is_whatsapp_candidate BOOLEAN DEFAULT true,
    UNIQUE(chapter_id, version_number)
);

-- Track edit conversations
CREATE TABLE image_edit_conversations (
    id SERIAL PRIMARY KEY,
    image_version_id INTEGER REFERENCES image_versions(id),
    telegram_user_id BIGINT NOT NULL,
    telegram_message_id BIGINT NOT NULL,
    edit_request TEXT NOT NULL,
    processed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Implementation:**
```python
class TelegramEditHandler:
    def handle_reply(self, message):
        """
        1. Check if reply is to an image message
        2. Extract edit request from message text
        3. Verify it's a legitimate edit (not random chat)
        4. Get original image and prompt
        5. Send edit request to image model
        6. Generate new version
        7. Post as reply with version number
        8. Mark old version as superseded
        """
        
    def is_valid_edit_request(self, text: str) -> bool:
        """
        Use LLM to determine if message is an edit request
        vs. unrelated conversation
        
        Valid: "Make the sky more blue", "Add a tree", "Remove the person"
        Invalid: "Thanks!", "Looks good", "When is this being posted?"
        """
```

**Telegram Webhook Changes:**
```python
# api.py
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    # Handle reactions (existing)
    if 'message_reaction' in data:
        # ... existing code ...
    
    # NEW: Handle replies for edits
    if 'message' in data:
        message = data['message']
        if 'reply_to_message' in message:
            # This is a reply - check if it's an edit request
            await handle_edit_request(message)
```

---

### 6. No Image Versioning ⚠️

**Current Implementation:**
```python
# chapters table has single image_path
ALTER TABLE chapters ADD COLUMN image_path TEXT;
```

**Problem:**
- Only stores one image per chapter
- No version history
- Can't track edits or go back to previous versions
- No lineage tracking

**Solution:**
- Use `image_versions` table (see above)
- Track parent-child relationships
- Mark which version is active for WhatsApp
- Support manual override to revert to old version

**CLI Commands:**
```bash
# List all versions for a chapter
python main.py list-image-versions <chapter_id>

# Set active version for WhatsApp
python main.py set-active-image <image_version_id>

# View version history
python main.py image-history <chapter_id>
```

---

### 7. Episode-Halacha Relationship ⚠️

**Current Implementation:**
```python
# One episode = multiple "chapters" (auto-generated)
# But these aren't Rambam chapters or halachot
```

**Problem:**
- Current model assumes "chapters" are subdivisions of episodes
- In reality: **One class episode covers multiple halachot** (possibly across Rambam chapter boundaries)
- Example: 45-minute class might cover Shabbat 2:5 through 3:8
- Need to track: Episode → Multiple Halachot

**Solution:**
- Remove concept of "chapters" as episode subdivisions
- Use alignment data to map episode → halachot
- One episode maps to many halachot (possibly across multiple Rambam chapters)

**Updated Data Model:**
```
Episode (45 min class)
  ├─ Alignment 1: Shabbat 2:5 (0:00-5:30)
  ├─ Alignment 2: Shabbat 2:6 (5:30-12:00)
  ├─ Alignment 3: Shabbat 2:7 (12:00-18:45)
  ├─ Alignment 4: Shabbat 3:1 (18:45-25:00)  ← Crosses Rambam chapter boundary!
  └─ Alignment 5: Shabbat 3:2 (25:00-45:00)

Images Generated (LLM decides per halacha):
  - Halacha 2:5 → 1 diagram
  - Halacha 2:6 → 0 images (purely textual)
  - Halacha 2:7 → 2 images (illustration + infographic)
  - Halacha 3:1 → 1 illustration
  - Halacha 3:2 → 0 images
```

---

## Architectural Changes Required

### 1. New Pipeline Flow

**OLD:**
```
1. Download audio
2. Transcribe
3. Split into chapters (provider or LLM)
4. Generate image per chapter
5. Post to Telegram
```

**NEW:**
```
1. Download audio
2. Dual transcription (sofer.ai + Whisper)
3. Fetch Sefaria text for class's current position
4. Align transcript to Sefaria halachot (4-pass LLM)
5. Standardize Rambam references (LLM)
6. **For each halacha: LLM decides 0-N images**
7. Generate decided images
8. Post to Telegram voting group
9. Monitor for edit requests
10. Generate new versions on request
11. Tally votes when window expires
12. Blast approved images to WhatsApp
```

### 2. Remove "Chapter Splitting" Concept

**Remove:**
- `chapter_splitter.py` entirely (wrong abstraction)
- Provider-based "chapter" detection
- LLM-based "topic splitting"

**Replace with:**
- `text_aligner.py` - maps transcript to halachot
- Halacha-level granularity (e.g., Shabbat 2:5, 2:6, 2:7)
- No "chapter splitting" - just halacha alignment

### 3. Image Generation Strategy

**Current:** One image per "chapter" (auto-detected, wrong concept)

**New:** LLM decides 0-N images per halacha

**Implementation:**
```python
def generate_halacha_images(episode, alignments):
    """
    For each halacha covered:
    1. LLM analyzes halacha content
    2. LLM decides: 0, 1, 2, or 3 images needed
    3. LLM decides: image type for each (diagram, illustration, etc.)
    4. Generate decided images
    """
    
    images = []
    for alignment in alignments:
        # LLM decision
        decisions = image_decision_maker.decide_for_halacha({
            'chapter': alignment['chapter_num'],
            'halacha': alignment['halacha_num'],
            'hebrew_text': alignment['source_text'],
            'transcript': alignment['transcript_segment'],
            'summary': alignment['summary']
        })
        
        # Generate each decided image
        for decision in decisions:
            if decision['generate']:
                image = generate_image(
                    halacha_ref=f"{alignment['chapter_num']}:{alignment['halacha_num']}",
                    image_type=decision['image_type'],
                    prompt_focus=decision['prompt_focus']
                )
                images.append(image)
    
    return images
```

---

## Configuration Changes Required

### config.yaml Updates

```yaml
# REMOVE:
rss:
  feed_url: "..."

# ADD:
classes:
  - id: "cohen-shabbat"
    name: "Rabbi Cohen - Hilchot Shabbat"
    teacher: "Rabbi Cohen"
    rss_feed_url: "https://feeds.example.com/cohen-shabbat.rss"
    sefaria_ref: "Mishneh Torah, Shabbat"
    language: "he"
    
  - id: "levy-shabbat"
    name: "Rabbi Levy - Hilchot Shabbat"
    teacher: "Rabbi Levy"
    rss_feed_url: "https://feeds.example.com/levy-shabbat.rss"
    sefaria_ref: "Mishneh Torah, Shabbat"
    language: "he"

# UPDATE:
chapters:
  # REMOVE: strategy: "both"
  # ADD:
  strategy: "sefaria_alignment"  # Primary method: align to halachot
  fallback_strategy: "llm"  # Only for non-Rambam content
  
  # Halacha reference standardization
  standardization:
    enabled: true
    llm:
      provider: "anthropic"
      model: "claude-sonnet-4-20250514"

# ADD:
image_editing:
  enabled: true
  max_versions_per_chapter: 10
  edit_request_validation:
    use_llm: true  # Validate edit requests to avoid noise
    min_confidence: 0.7

# ADD:
image_generation:
  # ... existing ...
  decision_strategy: "llm_per_halacha"  # LLM decides 0-N images per halacha
  max_images_per_halacha: 3
  
telegram:
  # ... existing ...
  # ADD:
  edit_monitoring:
    enabled: true
    check_interval_seconds: 30
```

### prompts.yaml Updates

```yaml
# ADD:
chapter_name_standardization:
  system: |
    You are an expert in Jewish texts and Sefaria's reference system.
    Your job is to standardize chapter names to match Sefaria's canonical format.
  
  user: |
    The teacher mentioned this chapter name: "{detected_name}"
    
    Context from transcript: {context}
    
    Expected book: {expected_book}
    
    Return JSON:
    {{
      "standardized_name": "Mishneh Torah, Shabbat 3",
      "sefaria_ref": "Mishneh Torah, Shabbat 3",
      "confidence": 0.95,
      "reasoning": "..."
    }}

# ADD:
edit_request_validation:
  system: |
    You determine if a Telegram message is a legitimate image edit request
    or just casual conversation.
  
  user: |
    Message: "{message_text}"
    
    Is this an edit request for an image?
    
    Return JSON:
    {{
      "is_edit_request": true/false,
      "confidence": 0.95,
      "extracted_request": "Make the sky more blue" or null
    }}

# ADD:
chapter_image_prompt:
  system: |
    You create image prompts for individual halachot from Rambam.
  
  user: |
    Create image prompt(s) for this halacha:
    
    Reference: Mishneh Torah, {book_name} {chapter_num}:{halacha_num}
    
    Hebrew text: {hebrew_text}
    
    Teacher's explanation: {transcript_segment}
    
    Summary: {summary}
    
    Generate appropriate image prompt(s) for this specific halacha.
```

---

## New Files Required

### Core Application

1. **`src/class_manager.py`** - Manage multiple classes/feeds
```python
class ClassManager:
    def get_all_classes(self) -> list[Class]
    def get_class_by_id(self, class_id: str) -> Class
    def get_class_progress(self, class_id: str) -> dict
    def update_progress(self, class_id: str, chapter: int, halacha: int)
```

2. **`src/sefaria_ref_standardizer.py`** - Standardize Rambam references
```python
class SefariaRefStandardizer:
    def standardize(self, detected_ref: str, context: str) -> dict
    def validate_sefaria_ref(self, ref: str) -> bool
```

3. **`src/image_version_manager.py`** - Track image versions
```python
class ImageVersionManager:
    def create_version(self, chapter_id: int, image_path: str, prompt: str) -> int
    def create_edit_version(self, parent_id: int, edit_request: str) -> int
    def get_active_version(self, chapter_id: int) -> ImageVersion
    def set_active_version(self, version_id: int)
    def get_version_history(self, chapter_id: int) -> list[ImageVersion]
```

4. **`src/telegram_edit_handler.py`** - Handle edit requests
```python
class TelegramEditHandler:
    def handle_reply(self, message: dict)
    def is_valid_edit_request(self, text: str) -> bool
    def extract_edit_request(self, text: str) -> str
    def generate_edited_image(self, original_version_id: int, edit_request: str)
```

5. **`src/image_editor.py`** - Direct image model editing
```python
class ImageEditor:
    def edit_image(self, original_image_url: str, edit_instruction: str) -> str
    # Uses image model's native editing capability
    # For DALL-E: variations or edits API
    # For Flux: img2img with instruction
```

### Database Migrations

6. **`migrations/005_add_classes.sql`**
7. **`migrations/006_add_class_progress.sql`**
8. **`migrations/007_add_image_versions.sql`**
9. **`migrations/008_add_edit_conversations.sql`**
10. **`migrations/009_update_chapters_for_rambam.sql`**

---

## Files to Modify

### Major Modifications

1. **`src/pipeline.py`**
   - Add class selection logic
   - Replace "chapter splitting" with halacha alignment
   - Add Rambam reference standardization
   - Add image versioning
   - Add edit monitoring

2. **`src/chapter_splitter.py`**
   - DEPRECATE entirely for Rambam content
   - Or rename to `content_segmenter.py` for non-Rambam use only

3. **`src/telegram_poster.py`**
   - Add edit monitoring
   - Handle reply messages
   - Post image versions as replies

4. **`src/state.py`**
   - Add class management methods
   - Add image version methods
   - Add progress tracking methods

5. **`config.yaml`**
   - Replace single RSS with classes array
   - Update chapter strategy
   - Add image editing config

6. **`prompts.yaml`**
   - Add standardization prompts
   - Add edit validation prompts
   - Update image prompts for chapter-level

### Minor Modifications

7. **`src/rss_parser.py`**
   - Support multiple feeds
   - Add class_id to Episode

8. **`src/image_generator.py`**
   - Add edit/variation support
   - Support img2img for edits

9. **`main.py`**
   - Add class management commands
   - Add image version commands
   - Add progress tracking commands

---

## CLI Commands to Add

```bash
# Class management
python main.py list-classes
python main.py add-class --name "..." --teacher "..." --feed "..." --sefaria-ref "..."
python main.py class-progress <class_id>
python main.py compare-classes  # Show which chapters each class has covered

# Image versioning
python main.py list-image-versions <chapter_id>
python main.py set-active-image <version_id>
python main.py image-history <chapter_id>
python main.py revert-image <chapter_id> <version_id>

# Halacha reference standardization
python main.py standardize-ref "Hilchos Shabbos Perek Gimmel Halacha Hey"
python main.py validate-sefaria-ref "Mishneh Torah, Shabbat 3:5"

# Testing
python main.py test-edit-detection "Make the sky more blue"
python main.py test-alignment <episode_guid>
```

---

## Testing Strategy Updates

### New Test Cases

1. **Multi-class processing**
   - Process episodes from 3 different classes
   - Verify each tracked separately
   - Check progress updates correctly

2. **Halacha reference standardization**
   - Test various input formats ("Perek Gimmel", "Chapter 3", etc.)
   - Verify Sefaria ref validation
   - Check confidence scores

3. **Image versioning**
   - Generate initial image
   - Request 3 edits
   - Verify version lineage
   - Test revert functionality

4. **Edit request validation**
   - Test legitimate edit requests
   - Test casual conversation (should reject)
   - Test edge cases

5. **Cross-chapter episodes**
   - Episode covering Shabbat 2:8 through 3:5 (crosses Rambam chapter boundary)
   - Verify correct halacha alignment
   - Check image generation per halacha (LLM decides)

---

## Migration Path

### Phase 1: Database Schema (Week 1)
1. Create classes table
2. Create class_progress table
3. Create image_versions table
4. Create image_edit_conversations table
5. Migrate existing episodes to default class

### Phase 2: Multi-Class Support (Week 2)
1. Implement ClassManager
2. Update config.yaml format
3. Update RSSParser for multiple feeds
4. Update pipeline to process per class
5. Add CLI commands for class management

### Phase 3: Rambam Reference Standardization (Week 2)
1. Implement SefariaRefStandardizer
2. Add prompts
3. Integrate into alignment pipeline
4. Test with various input formats (Hebrew/English/mixed)

### Phase 4: Image Versioning (Week 3)
1. Implement ImageVersionManager
2. Update database queries
3. Update Telegram poster
4. Add CLI commands

### Phase 5: Edit Workflow (Week 3-4)
1. Implement TelegramEditHandler
2. Implement ImageEditor
3. Update webhook to handle replies
4. Add edit validation
5. Test end-to-end edit flow

### Phase 6: Integration & Testing (Week 4)
1. End-to-end testing with real data
2. Test multiple classes simultaneously
3. Test edit workflow
4. Performance optimization

---

## Breaking Changes

### Config Format
- `rss.feed_url` → `classes[]` array
- `chapters.strategy: "both"` → REMOVED (wrong concept)
- Alignment works at halacha level, not "chapter splitting"

### Database Schema
- `episodes` table needs `class_id` column
- Remove "chapters" table concept (wrong abstraction)
- Alignments map episodes → halachot directly
- New tables: classes, class_progress, image_versions, image_edit_conversations

### API Changes
- `Pipeline.run()` needs class_id parameter
- Remove `ChapterSplitter` - wrong abstraction
- Image generation returns version_id not just path
- Images linked to halachot, not "chapters"

---

## Backward Compatibility

### Option 1: Clean Break
- Require full migration
- No backward compatibility
- Faster implementation

### Option 2: Gradual Migration
- Support both old and new config formats
- Default class for single-feed mode
- Deprecation warnings
- Remove old code in v2.0

**Recommendation:** Option 1 (Clean Break)
- This is a major architectural change
- Trying to maintain compatibility will complicate code
- Better to migrate cleanly and document process

---

## Documentation Updates Needed

1. **Migration Guide**
   - How to convert old config to new format
   - Database migration steps
   - Data migration for existing episodes
   - Understanding halacha vs chapter terminology

2. **Multi-Class Guide**
   - How to set up multiple classes
   - How to track progress
   - How to compare coverage

3. **Image Editing Guide**
   - How volunteers request edits
   - What makes a valid edit request
   - How to manage versions

4. **Sefaria Integration Guide**
   - How halacha alignment works (NOT "chapter splitting")
   - How to configure Sefaria references
   - Troubleshooting alignment issues
   - Understanding Rambam structure (chapters contain halachot)

---

## Open Questions

1. **Image Generation Granularity**
   - LLM decides 0-N images per halacha (CONFIRMED)
   - Not "one per chapter" - that was wrong
   - Each halacha analyzed independently

2. **Edit Request Approval**
   - Should edits require approval before generation?
   - Or generate immediately and let voting decide?

3. **Cross-Chapter Episodes**
   - If episode covers chapters 2-4, generate 3 images?
   - Or one composite image?

4. **Halacha Reference Conflicts**
   - What if standardization confidence is low?
   - Manual review required?
   - Fallback behavior?

5. **Image Version Limits**
   - Max versions per chapter?
   - Auto-cleanup old versions?
   - Storage considerations?

---

## Estimated Effort

| Task | Effort | Priority |
|------|--------|----------|
| Database schema changes | 2 days | P0 |
| Multi-class support | 3 days | P0 |
| Halacha reference standardization | 2 days | P0 |
| Remove "chapter splitting" concept | 2 days | P0 |
| Image versioning | 2 days | P1 |
| Edit workflow | 4 days | P1 |
| Testing & integration | 3 days | P0 |
| Documentation | 2 days | P1 |
| **Total** | **20 days** | |

---

## Conclusion

The current codebase has a solid foundation but requires significant architectural changes to support:
- Multiple classes/teachers
- Halacha-level alignment to Rambam (NOT "chapter splitting")
- Interactive image editing
- Version management

The biggest change is removing the generic "chapter splitting" concept entirely and replacing it with Sefaria-aligned, halacha-based mapping. This fundamentally changes how the pipeline works but aligns perfectly with the use case of processing Rambam classes.

**Recommendation:** Proceed with clean break migration, implement in phases, prioritize core functionality (multi-class + halacha alignment) before advanced features (editing).
# 🧠 Deep Architectural Analysis & Design Decisions

## Critical Design Flaws in Current Approach

### 1. Image Prompt Generation Anti-Pattern

**Current Approach (BAD):**
```yaml
image_prompt:
  style_suffix: "cinematic, dramatic lighting, high quality digital art, 16:9 aspect ratio"
```

**Problems:**
- Appending strings to prompts is fragile
- No context awareness
- Can't adapt style per content
- Hard to maintain consistency
- Prompt injection vulnerabilities

**Correct Approach:**
```yaml
image_generation:
  system_prompt: |
    You are a visual artist specializing in Jewish educational content.
    Your images must be:
    - Respectful and appropriate for religious audiences
    - Cinematic with dramatic lighting
    - High quality digital art in 16:9 aspect ratio
    - Free of text, people's faces, or identifiable figures
    - Symbolic and abstract when depicting Torah concepts
    
  style_guidelines:
    aspect_ratio: "16:9"
    quality: "high"
    mood: "contemplative, scholarly"
    color_palette: "warm earth tones, deep blues, golden accents"
    avoid: ["text", "faces", "modern technology", "anachronisms"]
```

**Implementation:**
- System prompt sets consistent style context
- LLM generates content-aware prompts within style boundaries
- Easier to A/B test different styles
- Can override per-class if needed

---

### 2. Sefaria Name Standardization via MCP

**Current Gap:** No clear strategy for mapping teacher's spoken names to Sefaria canonical refs

**Deep Problem:**
- Teacher says: "Hilchos Shabbos Perek Gimmel"
- Sefaria expects: "Mishneh Torah, Shabbat 3"
- Variations: "Shabbos", "Shabbat", "Hilchot", "Hilchos", "Chapter 3", "Perek 3", "פרק ג"
- Ambiguity: "Shabbat" could be Mishneh Torah OR Talmud Bavli OR Shulchan Aruch

**Solution: Sefaria MCP Integration**

```python
class SefariaNameResolver:
    """
    Use Sefaria MCP to get canonical names and disambiguate
    """
    
    def __init__(self):
        self.mcp_client = SefariaClient(use_mcp=True)
        self.cache = {}  # Cache resolved names
    
    def resolve(self, spoken_name: str, context: dict) -> dict:
        """
        1. Query Sefaria MCP for possible matches
        2. Use LLM to disambiguate if multiple matches
        3. Return canonical ref with confidence
        
        Args:
            spoken_name: "Hilchos Shabbos Chapter 3"
            context: {
                "class_sefaria_ref": "Mishneh Torah, Shabbat",
                "previous_chapter": 2,
                "transcript_excerpt": "..."
            }
        
        Returns:
            {
                "canonical_ref": "Mishneh Torah, Shabbat 3",
                "confidence": 0.98,
                "alternatives": [...],
                "sefaria_metadata": {...}
            }
        """
        
        # Step 1: Get all possible matches from Sefaria
        candidates = self.mcp_client.search_refs(spoken_name)
        
        # Step 2: Filter by expected book if known
        if context.get('class_sefaria_ref'):
            candidates = [c for c in candidates 
                         if c['book'] in context['class_sefaria_ref']]
        
        # Step 3: Use sequential context (previous chapter)
        if context.get('previous_chapter'):
            # Prefer next sequential chapter
            expected_chapter = context['previous_chapter'] + 1
            candidates = sorted(candidates, 
                              key=lambda c: abs(c['chapter'] - expected_chapter))
        
        # Step 4: LLM disambiguation if still ambiguous
        if len(candidates) > 1:
            return self._llm_disambiguate(spoken_name, candidates, context)
        
        return candidates[0] if candidates else None
```

**Key Insight:** Sequential context is powerful
- If last episode was Chapter 2, next is likely Chapter 3
- Reduces ambiguity dramatically
- Can detect when teacher skips chapters

---

### 3. Multi-Halacha Episode Complexity

**Scenario:** 45-minute class covers Shabbat 2:5 through 3:8 (multiple halachot, crossing Rambam chapter boundary)

**Questions:**
1. How many images to generate? **LLM decides per halacha (0-N each)**
2. What if teacher spends 30 min on one halacha, 2 min on another? **LLM considers depth/importance**
3. How to handle halachot that cross Rambam chapter boundaries? **Track at halacha level**

**Solution: LLM-Based Image Decision Per Halacha**

```python
class ImageDecisionMaker:
    """
    LLM analyzes each halacha independently
    Decides: 0, 1, 2, or 3 images needed
    """
    
    def decide_images_for_episode(self, alignments: list) -> list:
        """
        For each halacha covered in episode:
        - Analyze content, depth, visual potential
        - Decide image count and types
        - No grouping by Rambam chapter
        """
        
        all_image_specs = []
        
        for alignment in alignments:
            # LLM analyzes this specific halacha
            specs = self.decide_for_halacha({
                'chapter': alignment['chapter_num'],
                'halacha': alignment['halacha_num'],
                'hebrew_text': alignment['source_text'],
                'transcript': alignment['transcript_segment'],
                'duration_ms': alignment['end_ms'] - alignment['start_ms'],
                'teacher_emphasis': self._analyze_emphasis(alignment)
            })
            
            all_image_specs.extend(specs)
        
        return all_image_specs
```

---

### 4. Transcript-to-Text Alignment Edge Cases

**Case 1: Teacher Digresses**
```
Transcript: "So in halacha 5... actually, let me tell you a story about 
my Rebbe... [15 minutes of stories]... okay back to halacha 5..."
```

**Problem:** Alignment might map story to halacha 5
**Solution:** Detect digressions using discourse markers
- "Actually, let me tell you..."
- "By the way..."
- "This reminds me..."
- Mark as non-aligned content

**Case 2: Teacher Compares Halachot**
```
Transcript: "Halacha 5 says X, but remember in halacha 2 we learned Y, 
and this connects to halacha 8..."
```

**Problem:** Multiple halachot referenced in one segment
**Solution:** Primary vs. secondary references
- Primary: Current halacha being taught (5)
- Secondary: References for comparison (2, 8)
- Only align to primary halacha
- Track cross-references in metadata

**Case 3: Teacher Skips Halachot**
```
Transcript: "We'll skip halachot 6 and 7 because they're not relevant 
to our community. Moving to halacha 8..."
```

**Problem:** Gap detection might think they're covered
**Solution:** Explicit skip detection
- Listen for "skip", "not covering", "we'll come back to"
- Mark as intentionally skipped vs. accidentally missed

**Case 4: Teacher Reorders Halachot**
```
Transcript: "Before we do halacha 5, let's first understand halacha 7 
because it provides context..."
```

**Problem:** Non-sequential teaching
**Solution:** Track teaching order vs. canonical order
- Store both in database
- Images still generated per halacha (LLM decides)
- Note pedagogical reordering in metadata

---

### 5. Image Edit Workflow Deep Dive

**Problem:** How to distinguish edit requests from noise?

**Scenarios:**

**Valid Edit Requests:**
```
"Make the sky darker"
"Add more blue tones"
"Remove the person in the background"
"Make it more abstract"
"Less busy, more minimalist"
```

**Invalid (Noise):**
```
"Thanks!"
"Looks great"
"When will this be posted?"
"@username what do you think?"
"Can someone explain this halacha?"
```

**Ambiguous:**
```
"This doesn't feel right"  → Need clarification
"Too modern"  → Valid but vague
"Not Jewish enough"  → Valid but subjective
```

**Solution: Multi-Stage Validation**

```python
class EditRequestValidator:
    
    def validate(self, message: str, context: dict) -> dict:
        """
        Stage 1: Quick filter (regex/keywords)
        Stage 2: LLM classification
        Stage 3: Clarification if ambiguous
        """
        
        # Stage 1: Quick reject obvious noise
        if self._is_obvious_noise(message):
            return {'valid': False, 'reason': 'noise'}
        
        # Stage 2: LLM classification
        classification = self._llm_classify(message)
        
        if classification['confidence'] > 0.9:
            if classification['is_edit_request']:
                return {
                    'valid': True,
                    'edit_instruction': classification['extracted_instruction'],
                    'confidence': classification['confidence']
                }
            else:
                return {'valid': False, 'reason': 'not_edit_request'}
        
        # Stage 3: Ambiguous - ask for clarification
        if classification['confidence'] < 0.7:
            return {
                'valid': 'needs_clarification',
                'clarification_prompt': self._generate_clarification_prompt(message)
            }
        
        return classification
    
    def _is_obvious_noise(self, message: str) -> bool:
        """Quick regex checks"""
        noise_patterns = [
            r'^thanks?!*$',
            r'^(great|good|nice|cool)!*$',
            r'^when\s+(will|is)',
            r'@\w+',  # Mentions
            r'^\s*$'  # Empty
        ]
        return any(re.match(p, message.lower()) for p in noise_patterns)
```

**Clarification Flow:**
```
User: "This doesn't feel right"
Bot: "I'd like to help improve this image. Could you be more specific? 
      For example:
      - Colors (too bright/dark, wrong palette)
      - Composition (too busy, too empty)
      - Style (too modern, too abstract)
      - Content (missing elements, wrong theme)"

User: "Too bright, make it darker and more somber"
Bot: "Got it! Generating a darker, more somber version..."
```

---

### 6. Image Model Selection Strategy

**Current:** Single provider (DALL-E or Flux)

**Problem:** Different models have different strengths

**Insight:** Use different models for different purposes

```yaml
image_generation:
  initial_generation:
    provider: "replicate"  # Flux for initial high-quality
    model: "black-forest-labs/flux-1.1-pro"
  
  edits:
    provider: "openai_dalle"  # DALL-E better for edits
    model: "dall-e-3"
    use_variations: true
  
  fallback:
    provider: "stability_ai"  # If primary fails
```

**Strategy:**
- **Flux**: Best for initial generation, high quality, good with abstract concepts
- **DALL-E**: Best for edits/variations, understands natural language edits
- **Stability**: Fallback, most reliable, good for batch processing

**Edit Workflow:**
```python
def generate_edit(self, original_image_url: str, edit_request: str):
    """
    1. Try DALL-E edit API first (native editing)
    2. If fails, use Flux img2img with instruction
    3. If both fail, regenerate from scratch with modified prompt
    """
```

---

### 7. Voting System Game Theory

**Problem:** Volunteers might game the system

**Scenarios:**

**Scenario 1: Vote Brigading**
- One volunteer creates multiple accounts
- Upvotes their preferred style
- Downvotes others

**Solution: Reputation System**
```sql
CREATE TABLE volunteer_reputation (
    telegram_user_id BIGINT PRIMARY KEY,
    reputation_score FLOAT DEFAULT 1.0,
    total_votes INTEGER DEFAULT 0,
    agreement_rate FLOAT,  -- How often they agree with consensus
    last_updated TIMESTAMP
);

-- Weight votes by reputation
SELECT 
    SUM(CASE WHEN vote_type = 'upvote' THEN reputation_score ELSE 0 END) as weighted_upvotes,
    SUM(CASE WHEN vote_type = 'downvote' THEN reputation_score ELSE 0 END) as weighted_downvotes
FROM telegram_votes v
JOIN volunteer_reputation r ON v.user_id = r.telegram_user_id;
```

**Scenario 2: Approval Threshold Gaming**
- If threshold is 70%, volunteers might strategically vote to just meet it
- Or vote to just miss it

**Solution: Dynamic Thresholds**
```python
def calculate_approval_threshold(chapter_id: int, context: dict) -> float:
    """
    Adjust threshold based on:
    - Historical approval rates for this class
    - Importance of this chapter (key concepts vs. minor details)
    - Number of edit iterations (lower threshold after multiple edits)
    - Volunteer participation rate
    """
    base_threshold = 0.70
    
    # Lower threshold if this is 3rd+ edit iteration
    edit_count = context['edit_iteration']
    if edit_count > 2:
        base_threshold -= 0.05 * (edit_count - 2)
    
    # Raise threshold for key chapters
    if context['is_key_chapter']:
        base_threshold += 0.10
    
    # Adjust for participation
    if context['voter_count'] < 3:
        base_threshold -= 0.10  # More lenient if few voters
    
    return max(0.5, min(0.9, base_threshold))
```

**Scenario 3: Volunteer Fatigue**
- Too many images to vote on
- Volunteers stop participating

**Solution: Smart Batching**
```python
def batch_for_voting(images: list) -> list:
    """
    Don't post all images at once
    
    Strategy:
    - Post 3-5 images per day
    - Prioritize key chapters
    - Group by theme for easier comparison
    - Spread across different times for timezone coverage
    """
```

---

### 8. WhatsApp Subscriber Management

**Deep Problem:** How do people subscribe?

**Options:**

**Option 1: Telegram Bot Command**
```
User in Telegram: /subscribe +1234567890
Bot: "Added +1234567890 to WhatsApp distribution list"
```
**Pros:** Simple, centralized
**Cons:** Privacy concerns, requires phone number in Telegram

**Option 2: WhatsApp Opt-In Message**
```
User sends WhatsApp message to bot: "Subscribe Shabbat"
Bot: "You're subscribed to Hilchot Shabbat updates! Reply STOP to unsubscribe."
```
**Pros:** Privacy-friendly, WhatsApp-native
**Cons:** Requires WhatsApp Business API webhook setup

**Option 3: Web Form**
```
User fills form on website with phone number
System sends WhatsApp confirmation code
User replies with code to confirm
```
**Pros:** Most secure, prevents spam
**Cons:** More complex, requires web infrastructure

**Recommendation:** Option 2 + Option 3 hybrid
- Primary: WhatsApp opt-in (simple, privacy-friendly)
- Secondary: Web form for bulk signups (organizations)

**Unsubscribe Flow:**
```
User: "STOP"
Bot: "You've been unsubscribed. Reply START to resubscribe."

User: "STOP SHABBAT" (if subscribed to multiple)
Bot: "You've been unsubscribed from Hilchot Shabbat. 
      You're still subscribed to: Hilchot Tefillah, Hilchot Kashrut"
```

---

### 9. Cost Optimization Strategy

**Current Approach:** Process everything, no optimization

**Problem:** Costs can spiral
- Transcription: $0.25-1.00 per hour
- LLM calls: $0.01-0.10 per call
- Image generation: $0.04-0.20 per image
- Storage: $0.023 per GB/month

**45-minute episode cost breakdown:**
```
Dual transcription: $0.50 (sofer.ai) + $0.15 (Whisper) = $0.65
Alignment (4 LLM passes): $0.40
Chapter name standardization: $0.05
Image generation (3 chapters): $0.60
Edit iterations (avg 2 per image): $1.20
Storage (audio + transcripts + images): $0.10
Total per episode: ~$3.00

With 3 classes, 2 episodes/week each:
$3.00 × 6 episodes/week × 4 weeks = $72/month (just processing)
Plus AWS infrastructure: $65-95/month
Total: ~$140-170/month
```

**Optimization Strategies:**

**1. Caching Aggressively**
```python
# Cache Sefaria texts (rarely change)
# Cache alignment results (reuse for similar content)
# Cache image prompts (similar chapters)
```

**2. Batch Processing**
```python
# Process multiple episodes in one batch
# Reduces cold start costs
# Better resource utilization
```

**3. Smart Transcription**
```python
# Only use sofer.ai for Hebrew-heavy content
# Use cheaper Whisper for English segments
# Detect language first, then choose provider
```

**4. Image Generation Optimization**
```python
# Generate lower-res for voting
# Only generate high-res for approved images
# Reuse similar images across classes (same chapter, different teacher)
```

**5. LLM Call Reduction**
```python
# Batch alignment calls (process multiple halachot at once)
# Use cheaper models for simple tasks (name standardization)
# Cache common patterns
```

---

### 10. Data Retention & Privacy

**Problem:** Storing audio files forever is expensive and potentially problematic

**Questions:**
- How long to keep audio files?
- What about transcripts?
- What about images?
- GDPR/privacy concerns?

**Retention Policy:**

```yaml
retention:
  audio_files:
    keep_duration_days: 90  # Keep for 3 months
    archive_to_glacier: true  # Then move to cold storage
    delete_after_days: 365  # Delete after 1 year
  
  transcripts:
    keep_duration_days: 365  # Keep for 1 year
    anonymize_after_days: 180  # Remove speaker names after 6 months
  
  images:
    keep_all_versions: false
    keep_approved_versions: true
    keep_rejected_versions_days: 30
  
  personal_data:
    whatsapp_numbers:
      hash_after_days: 30  # Hash phone numbers after 30 days
      delete_inactive_after_days: 365  # Delete if no activity for 1 year
    
    telegram_user_ids:
      anonymize_votes_after_days: 90  # Keep votes but remove user IDs
```

**Implementation:**
```python
class RetentionManager:
    def run_retention_policy(self):
        """
        Daily cron job to enforce retention policy
        """
        self.archive_old_audio()
        self.delete_expired_audio()
        self.anonymize_old_transcripts()
        self.cleanup_rejected_images()
        self.hash_old_phone_numbers()
        self.delete_inactive_subscribers()
```

---

### 11. Multi-Language Support (Future)

**Current:** Hebrew-only focus

**Future:** Support multiple languages

**Challenges:**
- Different transcription providers per language
- Different Sefaria texts (Hebrew, English, translations)
- Different image styles per culture
- Different WhatsApp subscriber preferences

**Architecture:**
```yaml
classes:
  - id: "cohen-shabbat-hebrew"
    language: "he"
    transcription_provider: "sofer_ai"
    sefaria_language: "he"
    image_style: "traditional_jewish"
  
  - id: "cohen-shabbat-english"
    language: "en"
    transcription_provider: "openai_whisper"
    sefaria_language: "en"
    image_style: "modern_educational"
```

**Key Insight:** Language affects entire pipeline
- Not just transcription
- Also affects alignment (Hebrew text structure differs)
- Image prompts need cultural context
- WhatsApp messages need localization

---

### 12. Quality Assurance & Monitoring

**Problem:** How to detect when system is producing bad results?

**Metrics to Track:**

```python
class QualityMetrics:
    """
    Track quality metrics across pipeline
    """
    
    def track_transcription_quality(self):
        """
        - Word error rate (if ground truth available)
        - Confidence scores from provider
        - Manual spot checks
        """
    
    def track_alignment_quality(self):
        """
        - Alignment confidence scores (per halacha)
        - Gap detection accuracy
        - Manual review of random samples
        - Volunteer feedback on accuracy
        """
    
    def track_image_quality(self):
        """
        - Approval rates (per halacha)
        - Edit iteration counts
        - Volunteer satisfaction scores
        - Content policy violations
        - LLM decision accuracy (did it correctly decide image need?)
        """
    
    def track_delivery_quality(self):
        """
        - WhatsApp delivery success rate
        - Unsubscribe rates
        - Complaint rates
        - Engagement metrics
        """
```

**Alerting:**
```python
# Alert if alignment confidence drops below 0.7
# Alert if approval rate drops below 50%
# Alert if delivery failure rate exceeds 5%
# Alert if unsubscribe rate spikes
```

**Dashboard:**
```
- Episodes processed today/week/month
- Average alignment confidence
- Image approval rates
- Active subscribers
- Cost per episode
- Processing time per episode
```

---

## Architectural Principles

### 1. Separation of Concerns

**Bad:**
```python
def process_episode(episode):
    # Download, transcribe, align, generate images, post to telegram, vote, send whatsapp
    # All in one function
```

**Good:**
```python
# Each stage is independent
# Can retry individual stages
# Can test in isolation
# Can swap implementations
```

### 2. Idempotency

**Every operation should be idempotent:**
```python
# Running twice should produce same result
# No duplicate images
# No duplicate votes
# No duplicate WhatsApp messages
```

### 3. Graceful Degradation

**If one component fails, others continue:**
```python
# If image generation fails, still save transcript
# If voting fails, can manually approve
# If WhatsApp fails, can retry later
```

### 4. Observability

**Every operation should be logged and traceable:**
```python
# Structured logging
# Correlation IDs across services
# Metrics for every operation
# Traces for debugging
```

### 5. Configuration Over Code

**Behavior should be configurable:**
```python
# Don't hardcode thresholds
# Don't hardcode prompts
# Don't hardcode providers
# Make everything configurable
```

---

## Open Design Questions

### 1. Image Generation Granularity

**Question:** How many images per halacha?

**Answer:** LLM decides 0-N (max 3) per halacha
- Some halachot need no images (purely textual)
- Some need 1 image (simple concept)
- Some need 2-3 images (complex, multi-faceted)

**Implementation:** Already designed in image decision system

### 2. Cross-Class Image Reuse

**Question:** If two teachers cover same halacha, reuse images?

**Pros:**
- Cost savings
- Consistency
- Faster processing

**Cons:**
- Different teaching styles might need different images
- Different emphasis on different aspects
- Less personalization

**Recommendation:** Generate separately by default, but allow manual linking if images are identical

### 3. Real-Time vs. Batch Processing

**Question:** Process episodes immediately or in batches?

**Real-time:**
- Faster turnaround
- More responsive
- Higher costs (no batching optimization)

**Batch:**
- Lower costs
- Better resource utilization
- Slower turnaround

**Recommendation:** Hybrid
- Real-time for priority classes
- Batch for others
- Configurable per class

### 4. Volunteer Onboarding

**Question:** How to train new volunteers on voting?

**Ideas:**
- Tutorial images with examples
- Practice voting on test images
- Feedback on voting patterns
- Gamification (badges, leaderboards)

### 5. Content Moderation

**Question:** Who reviews images before WhatsApp blast?

**Options:**
- Fully automated (trust voting)
- Manual review by admin
- Hybrid (automated + spot checks)

**Recommendation:** Hybrid with escalation
- Auto-approve if >80% approval
- Manual review if 60-80%
- Auto-reject if <60%

---

This analysis goes much deeper into the actual implementation challenges, edge cases, and design decisions that will come up during development.
# 🎯 Implementation Plan V2 (Updated with Deep Analysis)

## Changes from V1

1. **Image prompt generation** - System prompts instead of string concatenation
2. **Sefaria name resolution** - MCP integration with disambiguation
3. **LLM-based image decisions** - Per halacha, 0-N images each
4. **Edit request validation** - Multi-stage with clarification
5. **Cost optimization** - Aggressive caching and smart provider selection
6. **Quality metrics** - Comprehensive monitoring and alerting
7. **Retention policies** - Data lifecycle management
8. **Removed reputation system** - Not needed for 5 volunteers
9. **Removed weighted chapter images** - Wrong abstraction (halachot, not chapters)

---

## Phase 0: Foundation Fixes (Week 1)

### 0.1: Fix Image Prompt Generation

**Remove:**
```yaml
image_prompt:
  style_suffix: "cinematic, dramatic lighting..."
```

**Replace with:**
```yaml
image_generation:
  system_prompt_file: "./prompts/image_system_prompt.yaml"
  
  style_config:
    aspect_ratio: "16:9"
    quality: "high"
    mood: "contemplative, scholarly"
    color_palette: "warm earth tones, deep blues, golden accents"
    avoid: ["text", "faces", "modern technology"]
    
  per_class_overrides:
    enabled: true  # Allow classes to customize style
```

**New file: `prompts/image_system_prompt.yaml`**
```yaml
default: |
  You are a visual artist specializing in Jewish educational content.
  
  Your images must be:
  - Respectful and appropriate for religious audiences
  - Symbolic and abstract when depicting Torah concepts
  - Free of text, identifiable people, or modern anachronisms
  - Cinematic with dramatic lighting
  - High quality digital art in 16:9 aspect ratio
  
  Color palette: Warm earth tones, deep blues, golden accents
  Mood: Contemplative, scholarly, timeless
  
  When depicting concepts from Hilchot Shabbat:
  - Use symbolic representations (candles, challah, wine)
  - Avoid literal depictions of people performing actions
  - Focus on atmosphere and spiritual essence
  - Use light and shadow to convey meaning

advanced_mode: |
  [More detailed instructions for complex chapters]
```

### 0.2: Sefaria MCP Integration

**New file: `src/sefaria_mcp_client.py`**
```python
class SefariaMCPClient:
    """
    Use Sefaria MCP for canonical name resolution
    """
    
    def __init__(self):
        self.mcp = SefariaClient(use_mcp=True)
        self.cache = SefariaCache()
    
    def get_canonical_ref(self, spoken_name: str, context: dict) -> dict:
        """
        Use MCP to get all possible matches, then disambiguate
        """
        # Query MCP for matches
        matches = self.mcp.search_refs(spoken_name)
        
        # Filter by context
        filtered = self._filter_by_context(matches, context)
        
        # Disambiguate if needed
        if len(filtered) > 1:
            return self._disambiguate(spoken_name, filtered, context)
        
        return filtered[0] if filtered else None
    
    def _filter_by_context(self, matches, context):
        """
        Use class's expected book and sequential context
        """
        # Filter by expected book
        if context.get('class_sefaria_ref'):
            matches = [m for m in matches 
                      if context['class_sefaria_ref'] in m['book']]
        
        # Prefer sequential chapters
        if context.get('previous_chapter'):
            expected = context['previous_chapter'] + 1
            matches = sorted(matches, 
                           key=lambda m: abs(m.get('chapter', 0) - expected))
        
        return matches
    
    def _disambiguate(self, spoken_name, candidates, context):
        """
        Use LLM to choose best match
        """
        prompt = f"""
        The teacher said: "{spoken_name}"
        
        Context:
        - Expected book: {context.get('class_sefaria_ref')}
        - Previous chapter: {context.get('previous_chapter')}
        - Transcript excerpt: {context.get('transcript_excerpt', '')[:200]}
        
        Possible matches from Sefaria:
        {json.dumps(candidates, indent=2)}
        
        Which is most likely? Return JSON with index and confidence.
        """
        
        result = self.llm.call(prompt)
        return candidates[result['index']]
```

---

## Phase 1: Database & Infrastructure (Week 1)

### 1.1: Enhanced Database Schema

**Add to migrations:**

```sql
-- Classes with enhanced metadata
CREATE TABLE classes (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    teacher_name TEXT,
    rss_feed_url TEXT UNIQUE NOT NULL,
    sefaria_book_ref TEXT NOT NULL,
    language TEXT DEFAULT 'he',
    status TEXT DEFAULT 'active',
    
    -- Style customization
    image_style_override JSONB,
    
    -- Processing preferences
    priority TEXT DEFAULT 'normal',  -- high, normal, low
    processing_mode TEXT DEFAULT 'batch',  -- realtime, batch
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Volunteer reputation system
CREATE TABLE volunteer_reputation (
    telegram_user_id BIGINT PRIMARY KEY,
    username TEXT,
    reputation_score FLOAT DEFAULT 1.0,
    total_votes INTEGER DEFAULT 0,
    agreement_rate FLOAT DEFAULT 0.0,
    last_vote_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Enhanced image versions with lineage
CREATE TABLE image_versions (
    id SERIAL PRIMARY KEY,
    chapter_id INTEGER REFERENCES chapters(id),
    version_number INTEGER NOT NULL,
    parent_version_id INTEGER REFERENCES image_versions(id),
    
    -- Image data
    image_path TEXT NOT NULL,
    s3_url TEXT,
    thumbnail_url TEXT,
    
    -- Generation metadata
    generation_prompt TEXT NOT NULL,
    system_prompt TEXT,
    model_used TEXT,
    generation_params JSONB,
    
    -- Edit tracking
    edit_request TEXT,
    edit_type TEXT,  -- 'initial', 'edit', 'variation', 'regeneration'
    
    -- Voting & approval
    telegram_message_id BIGINT,
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    approval_percentage FLOAT,
    
    -- Status
    status TEXT DEFAULT 'pending',
    is_whatsapp_candidate BOOLEAN DEFAULT true,
    
    -- Timestamps
    generated_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP,
    
    UNIQUE(chapter_id, version_number)
);

-- Quality metrics
CREATE TABLE quality_metrics (
    id SERIAL PRIMARY KEY,
    metric_type TEXT NOT NULL,  -- 'transcription', 'alignment', 'image', 'delivery'
    entity_type TEXT NOT NULL,  -- 'episode', 'chapter', 'image_version'
    entity_id INTEGER NOT NULL,
    
    metric_name TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    metadata JSONB,
    
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- Cost tracking
CREATE TABLE cost_tracking (
    id SERIAL PRIMARY KEY,
    episode_guid TEXT REFERENCES episodes(guid),
    service TEXT NOT NULL,  -- 'transcription', 'llm', 'image_generation', 'storage'
    provider TEXT NOT NULL,
    operation TEXT NOT NULL,
    cost_usd DECIMAL(10, 4) NOT NULL,
    metadata JSONB,
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- Retention policy tracking
CREATE TABLE retention_log (
    id SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,  -- 'archived', 'deleted', 'anonymized'
    reason TEXT,
    performed_at TIMESTAMP DEFAULT NOW()
);
```

### 1.2: Configuration Schema V2

**New `config.yaml` structure:**

```yaml
# =============================================================================
# Podcast Pipeline V2 — Configuration
# =============================================================================

# ---------------------------------------------------------------------------
# Classes (Multiple RSS Feeds)
# ---------------------------------------------------------------------------
classes:
  - id: "cohen-shabbat"
    name: "Rabbi Cohen - Hilchot Shabbat"
    teacher: "Rabbi Cohen"
    rss_feed_url: "https://feeds.example.com/cohen-shabbat.rss"
    sefaria_ref: "Mishneh Torah, Shabbat"
    language: "he"
    priority: "high"  # Process immediately
    processing_mode: "realtime"
    
    # Optional style override
    image_style:
      mood: "traditional, warm"
      color_palette: "sepia tones, golden light"
  
  - id: "levy-shabbat"
    name: "Rabbi Levy - Hilchot Shabbat"
    teacher: "Rabbi Levy"
    rss_feed_url: "https://feeds.example.com/levy-shabbat.rss"
    sefaria_ref: "Mishneh Torah, Shabbat"
    language: "he"
    priority: "normal"
    processing_mode: "batch"

# ---------------------------------------------------------------------------
# Transcription (Dual System)
# ---------------------------------------------------------------------------
transcription:
  primary_provider: "sofer_ai"
  timestamp_provider: "openai_whisper"
  
  sofer_ai:
    language: "he"
    model: "default"
  
  openai_whisper:
    model: "whisper-1"
    language: "he"
    response_format: "verbose_json"
    timestamp_granularities: ["word"]
  
  # Cost optimization
  language_detection:
    enabled: true  # Detect language first
    use_cheaper_for_english: true  # Use Whisper for English segments

# ---------------------------------------------------------------------------
# Sefaria Integration
# ---------------------------------------------------------------------------
sefaria:
  use_mcp: true
  mcp_server_url: "http://localhost:3000"  # If self-hosted
  cache_ttl_hours: 168  # Cache for 1 week
  
  name_resolution:
    use_sequential_context: true  # Use previous chapter for disambiguation
    confidence_threshold: 0.8
    
  text_fetching:
    language: "he"
    include_commentary: false
    batch_size: 10  # Fetch multiple halachot at once

# ---------------------------------------------------------------------------
# Text Alignment
# ---------------------------------------------------------------------------
text_alignment:
  strategy: "sefaria_primary"  # vs "llm_fallback"
  
  llm:
    provider: "anthropic"
    model: "claude-sonnet-4-20250514"
  
  # 4-pass configuration
  passes:
    header_detection:
      enabled: true
      patterns: ["hebrew", "english", "mixed"]
      confidence_threshold: 0.7
    
    gap_detection:
      enabled: true
      detect_explicit_skips: true  # "We'll skip halacha 6"
    
    content_matching:
      enabled: true
      use_semantic_similarity: true
      min_confidence: 0.75
    
    verification:
      enabled: true
      require_manual_review_below: 0.6
  
  # Edge case handling
  digression_detection:
    enabled: true
    markers: ["actually", "by the way", "let me tell you", "this reminds me"]
  
  reference_classification:
    enabled: true  # Distinguish primary vs secondary references

# ---------------------------------------------------------------------------
# Image Generation (Per Halacha)
# ---------------------------------------------------------------------------
image_generation:
  strategy: "llm_decision_per_halacha"  # LLM decides 0-N images per halacha
  
  system_prompt_file: "./prompts/image_system_prompt.yaml"
  
  # Provider selection
  initial_generation:
    provider: "replicate"
    model: "black-forest-labs/flux-1.1-pro"
  
  edits:
    provider: "openai_dalle"
    model: "dall-e-3"
    use_variations_api: true
  
  fallback:
    provider: "stability_ai"
  
  # Quality settings
  resolution:
    voting: "1024x576"  # Lower res for voting
    whatsapp: "1792x1024"  # High res for distribution
  
  # Cost optimization
  caching:
    enabled: true
    cache_similar_prompts: true
    similarity_threshold: 0.9

# ---------------------------------------------------------------------------
# Telegram Voting System
# ---------------------------------------------------------------------------
telegram:
  voting_group_chat_id: "-1001234567890"
  
  voting:
    window_hours: 24
    upvote_emoji: "👍"
    downvote_emoji: "👎"
    
    # Dynamic thresholds
    approval_threshold:
      base: 0.70
      adjust_for_iterations: true  # Lower after multiple edits
      adjust_for_importance: true  # Higher for key chapters
      min: 0.50
      max: 0.90
    
    min_votes:
      base: 3
      adjust_for_volunteer_count: true
  
  # Edit workflow
  edit_monitoring:
    enabled: true
    check_interval_seconds: 30
    
    validation:
      use_llm: true
      confidence_threshold: 0.7
      request_clarification_below: 0.5
    
    max_iterations_per_image: 5
  
  # Reputation system
  reputation:
    enabled: true
    weight_votes_by_reputation: true
    update_frequency_hours: 24

# ---------------------------------------------------------------------------
# WhatsApp Distribution
# ---------------------------------------------------------------------------
whatsapp:
  rate_limit_messages_per_second: 20
  
  subscription:
    method: "whatsapp_optin"  # vs "telegram_command", "web_form"
    confirmation_required: true
  
  delivery:
    retry_failed: true
    max_retries: 3
    retry_delay_seconds: 300
  
  # Subscriber preferences
  preferences:
    allow_per_class_subscription: true
    allow_frequency_control: true  # daily, weekly, etc.

# ---------------------------------------------------------------------------
# Cost Optimization
# ---------------------------------------------------------------------------
cost_optimization:
  caching:
    sefaria_texts: true
    alignment_results: true
    image_prompts: true
  
  batching:
    enabled: true
    batch_size: 5
    batch_window_minutes: 60
  
  provider_selection:
    use_cheapest_for_simple_tasks: true
    fallback_on_rate_limit: true

# ---------------------------------------------------------------------------
# Quality Assurance
# ---------------------------------------------------------------------------
quality:
  metrics:
    track_transcription_confidence: true
    track_alignment_confidence: true
    track_approval_rates: true
    track_delivery_success: true
  
  alerting:
    alignment_confidence_threshold: 0.7
    approval_rate_threshold: 0.5
    delivery_failure_threshold: 0.05
    unsubscribe_rate_threshold: 0.10
  
  manual_review:
    required_for_low_confidence: true
    confidence_threshold: 0.6

# ---------------------------------------------------------------------------
# Data Retention
# ---------------------------------------------------------------------------
retention:
  audio_files:
    keep_days: 90
    archive_to_glacier: true
    delete_after_days: 365
  
  transcripts:
    keep_days: 365
    anonymize_after_days: 180
  
  images:
    keep_all_versions: false
    keep_approved_only: true
    delete_rejected_after_days: 30
  
  personal_data:
    hash_phone_numbers_after_days: 30
    delete_inactive_subscribers_after_days: 365
    anonymize_votes_after_days: 90

# ---------------------------------------------------------------------------
# AWS Configuration
# ---------------------------------------------------------------------------
aws:
  region: "us-east-1"
  s3_bucket: "podcast-pipeline-assets"
  sqs_queue_url: "https://sqs.us-east-1.amazonaws.com/ACCOUNT/podcast-jobs"
  
  storage:
    audio_prefix: "audio/"
    transcript_prefix: "transcripts/"
    image_prefix: "images/"
    
    lifecycle_policies:
      audio_to_glacier_days: 90
      delete_audio_days: 365

# ---------------------------------------------------------------------------
# Pipeline Behavior
# ---------------------------------------------------------------------------
pipeline:
  prompts_file: "./prompts.yaml"
  state_db_url: "postgresql://user:pass@host:5432/podcast_pipeline"
  
  processing:
    mode: "hybrid"  # realtime for high-priority, batch for others
    max_concurrent_episodes: 3
    image_concurrency: 2
  
  logging:
    level: "INFO"
    structured: true
    correlation_ids: true
  
  monitoring:
    enable_metrics: true
    enable_tracing: true
    dashboard_url: "https://dashboard.example.com"
```

---

## Phase 2: Core Modules (Week 2-3)

### 2.1: Sefaria Name Resolver

**File: `src/sefaria_name_resolver.py`**

Implements:
- MCP integration
- Sequential context disambiguation
- Confidence scoring
- Caching

### 2.2: LLM-Based Image Decision Per Halacha

**File: `src/image_decision_maker.py`**

```python
class ImageDecisionMaker:
    def decide_for_halacha(self, halacha_data):
        """
        LLM analyzes halacha and decides:
        - Should generate image? (yes/no)
        - How many? (0-3)
        - What types? (illustration, diagram, infographic, etc.)
        """
```

### 2.3: Edit Request Validator

**File: `src/edit_request_validator.py`**

```python
class EditRequestValidator:
    def validate(self, message, context):
        """
        Multi-stage validation:
        1. Quick filter (regex)
        2. LLM classification
        3. Clarification if ambiguous
        """
        # Stage 1
        if self._is_obvious_noise(message):
            return {'valid': False, 'reason': 'noise'}
        
        # Stage 2
        classification = self._llm_classify(message)
        
        if classification['confidence'] > 0.9:
            return classification
        
        # Stage 3
        if classification['confidence'] < 0.7:
            return {
                'valid': 'needs_clarification',
                'prompt': self._generate_clarification_prompt(message)
            }
        
        return classification
```

### 2.4: Cost Tracker

**File: `src/cost_tracker.py`**

```python
class CostTracker:
    def track_operation(self, episode_guid, service, provider, operation, cost):
        """
        Track cost of every operation
        """
        self.db.insert_cost(
            episode_guid=episode_guid,
            service=service,
            provider=provider,
            operation=operation,
            cost_usd=cost,
            metadata={'timestamp': datetime.now()}
        )
    
    def get_episode_cost(self, episode_guid):
        """
        Total cost for episode
        """
        return self.db.sum_costs(episode_guid=episode_guid)
    
    def get_monthly_cost(self):
        """
        Total cost for current month
        """
        return self.db.sum_costs(
            start_date=datetime.now().replace(day=1)
        )
```

### 2.5: Quality Metrics Tracker

**File: `src/quality_metrics.py`**

```python
class QualityMetrics:
    def track_alignment_quality(self, episode_guid, alignments):
        """
        Track alignment confidence scores
        """
        avg_confidence = sum(a['confidence'] for a in alignments) / len(alignments)
        
        self.db.insert_metric(
            metric_type='alignment',
            entity_type='episode',
            entity_id=episode_guid,
            metric_name='avg_confidence',
            metric_value=avg_confidence
        )
        
        # Alert if below threshold
        if avg_confidence < self.config['quality']['alerting']['alignment_confidence_threshold']:
            self.alert('Low alignment confidence', episode_guid, avg_confidence)
```

### 2.6: Retention Manager

**File: `src/retention_manager.py`**

```python
class RetentionManager:
    def run_daily_retention(self):
        """
        Daily cron job to enforce retention policies
        """
        self.archive_old_audio()
        self.delete_expired_audio()
        self.anonymize_old_transcripts()
        self.cleanup_rejected_images()
        self.hash_old_phone_numbers()
        self.delete_inactive_subscribers()
        
        # Log all actions
        self.log_retention_actions()
```

---

## Phase 3: Integration & Testing (Week 4)

### 3.1: End-to-End Testing

Test scenarios:
1. Multi-class processing (3 classes simultaneously)
2. Cross-chapter episode (covers chapters 2-4)
3. Edit workflow (request 3 edits, verify versions)
4. Reputation system (simulate voting patterns)
5. Cost tracking (verify all costs recorded)
6. Retention policies (verify data lifecycle)

### 3.2: Performance Testing

- Process 10 episodes concurrently
- Measure latency at each stage
- Identify bottlenecks
- Optimize slow operations

### 3.3: Cost Analysis

- Run for 1 week with real data
- Measure actual costs
- Compare to estimates
- Optimize expensive operations

---

## Migration from V1

### Breaking Changes

1. Config format completely changed
2. Database schema significantly expanded
3. Chapter splitting replaced with alignment
4. Image generation uses system prompts
5. Voting uses reputation weighting

### Migration Steps

1. Export existing data
2. Run database migrations
3. Convert config to new format
4. Create default class for existing episodes
5. Regenerate images with new system
6. Test thoroughly before production

---

## Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1 | Foundation | Fixed prompts, Sefaria MCP, DB schema |
| 2 | Core Modules | Name resolver, weighted images, edit validator |
| 3 | Advanced Features | Reputation, cost tracking, quality metrics |
| 4 | Integration | End-to-end testing, optimization |
| 5 | Deployment | AWS setup, monitoring, documentation |
| 6 | Polish | Bug fixes, performance tuning, training |

---

## Success Metrics

- Alignment confidence >85%
- Image approval rate >70%
- Cost per episode <$3
- Processing time <30 minutes
- Volunteer satisfaction >4/5
- WhatsApp delivery success >95%

---

This updated plan incorporates all the deep analysis findings and provides a more robust, production-ready architecture.
# 📸 Image Generation Decision System - Addendum

## Core Principle: LLM Decides Image Generation

**Key Insight:** Not every halacha needs an image. Some need multiple. LLM decides.

---

## Image Decision Process

### Step 1: LLM Analyzes Content

```python
class ImageDecisionMaker:
    """
    LLM determines:
    1. Should this halacha/chapter get an image?
    2. If yes, how many images?
    3. What type of image? (illustration, diagram, infographic, chart)
    """
    
    def decide_images(self, halacha_content: dict) -> list[ImageSpec]:
        """
        Args:
            halacha_content: {
                'chapter': 3,
                'halacha': 5,
                'hebrew_text': '...',
                'transcript_segment': '...',
                'summary': '...',
                'themes': ['measurement', 'time', 'prohibition']
            }
        
        Returns:
            [
                {
                    'generate': True,
                    'image_type': 'diagram',
                    'reason': 'Explains measurement concept',
                    'prompt_focus': 'Visual representation of shiur/measurement',
                    'priority': 'high'
                },
                {
                    'generate': True,
                    'image_type': 'infographic',
                    'reason': 'Timeline of events',
                    'prompt_focus': 'Sequence of actions before Shabbat',
                    'priority': 'medium'
                }
            ]
        """
        
        prompt = self._build_decision_prompt(halacha_content)
        response = self.llm.call(prompt)
        
        return self._parse_image_specs(response)
```

### Step 2: Prompt Template

```yaml
# prompts.yaml
image_decision:
  system: |
    You are an educational content strategist for Torah learning materials.
    
    Your job: Decide if visual content would enhance understanding of this halacha.
    
    Guidelines:
    - Generate images when they ADD VALUE (not just decoration)
    - Some halachot are purely textual/legal - no image needed
    - Some halachot benefit from multiple visual representations
    - Consider: diagrams, infographics, charts, illustrations, timelines
    
    Image types:
    - illustration: Symbolic/artistic representation of concept
    - diagram: Technical/structural explanation
    - infographic: Data/process visualization
    - chart: Comparative/categorical information
    - timeline: Sequential/temporal relationships
    - map: Spatial/geographical concepts
  
  user: |
    Analyze this halacha and decide on image generation:
    
    Chapter {chapter}, Halacha {halacha}
    
    Hebrew text:
    {hebrew_text}
    
    Teacher's explanation:
    {transcript_segment}
    
    Summary:
    {summary}
    
    Key themes: {themes}
    
    ---
    
    Return JSON array of image specifications:
    [
      {{
        "generate": true/false,
        "image_type": "illustration|diagram|infographic|chart|timeline|map",
        "reason": "Why this image is needed (or why not)",
        "prompt_focus": "What the image should emphasize",
        "priority": "high|medium|low",
        "estimated_complexity": "simple|moderate|complex"
      }}
    ]
    
    Return empty array [] if no images needed.
    
    Examples:
    - Halacha about abstract legal principle → []
    - Halacha about measurements → [diagram]
    - Halacha about sequence of actions → [infographic, timeline]
    - Halacha comparing multiple opinions → [chart]
```

---

## Database Schema Updates

### Add Image Type Tracking

```sql
-- Update image_versions table
ALTER TABLE image_versions ADD COLUMN image_type TEXT;
ALTER TABLE image_versions ADD COLUMN generation_reason TEXT;
ALTER TABLE image_versions ADD COLUMN prompt_focus TEXT;
ALTER TABLE image_versions ADD COLUMN priority TEXT;
ALTER TABLE image_versions ADD COLUMN complexity TEXT;

-- Add constraint
ALTER TABLE image_versions ADD CONSTRAINT image_type_check 
CHECK (image_type IN ('illustration', 'diagram', 'infographic', 'chart', 'timeline', 'map', NULL));

-- Track decision metadata
CREATE TABLE image_generation_decisions (
    id SERIAL PRIMARY KEY,
    chapter_id INTEGER REFERENCES chapters(id),
    halacha_num INTEGER NOT NULL,
    
    -- Decision
    should_generate BOOLEAN NOT NULL,
    image_count INTEGER DEFAULT 0,
    decision_reason TEXT,
    
    -- LLM metadata
    llm_model TEXT,
    llm_confidence FLOAT,
    decision_prompt TEXT,
    decision_response TEXT,
    
    decided_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(chapter_id, halacha_num)
);

-- Link images to decisions
ALTER TABLE image_versions ADD COLUMN decision_id INTEGER REFERENCES image_generation_decisions(id);
```

---

## Configuration: Maximum Configurability

### Enhanced config.yaml

```yaml
# =============================================================================
# Image Generation Decision System
# =============================================================================
image_generation:
  
  # Decision-making
  decision:
    enabled: true
    llm:
      provider: "anthropic"
      model: "claude-sonnet-4-20250514"
      temperature: 0.3  # Lower for more consistent decisions
    
    # Override: Force generation for all halachot
    force_generate_all: false
    
    # Override: Skip generation entirely
    skip_generation: false
    
    # Per-class overrides
    class_overrides:
      "cohen-shabbat":
        force_generate_all: false
        preferred_types: ["diagram", "infographic"]
      "levy-shabbat":
        force_generate_all: true
        preferred_types: ["illustration"]
  
  # Image type configuration
  image_types:
    illustration:
      enabled: true
      system_prompt_override: null
      style_config:
        mood: "symbolic, artistic"
        complexity: "moderate"
    
    diagram:
      enabled: true
      system_prompt_override: "./prompts/diagram_system_prompt.yaml"
      style_config:
        mood: "technical, clear"
        complexity: "simple"
        include_labels: true
        include_arrows: true
    
    infographic:
      enabled: true
      system_prompt_override: "./prompts/infographic_system_prompt.yaml"
      style_config:
        mood: "educational, structured"
        layout: "vertical"
        include_icons: true
    
    chart:
      enabled: true
      system_prompt_override: "./prompts/chart_system_prompt.yaml"
      style_config:
        chart_type: "comparison"  # comparison, hierarchy, flow
        include_legend: true
    
    timeline:
      enabled: true
      system_prompt_override: "./prompts/timeline_system_prompt.yaml"
      style_config:
        orientation: "horizontal"
        include_timestamps: true
    
    map:
      enabled: false  # Rarely needed for Rambam
  
  # Model selection per image type
  model_selection:
    illustration:
      provider: "replicate"
      model: "black-forest-labs/flux-1.1-pro"
    
    diagram:
      provider: "openai_dalle"  # Better at structured content
      model: "dall-e-3"
    
    infographic:
      provider: "openai_dalle"
      model: "dall-e-3"
    
    chart:
      provider: "openai_dalle"
      model: "dall-e-3"
    
    timeline:
      provider: "replicate"
      model: "black-forest-labs/flux-1.1-pro"
  
  # Generation parameters per type
  generation_params:
    illustration:
      width: 1344
      height: 768
      guidance: 3.5
      steps: 28
    
    diagram:
      width: 1024
      height: 1024  # Square for diagrams
      quality: "hd"
      style: "natural"  # Less artistic
    
    infographic:
      width: 768
      height: 1344  # Vertical
      quality: "hd"
    
    chart:
      width: 1024
      height: 768
      quality: "standard"
    
    timeline:
      width: 1792
      height: 768  # Wide
      guidance: 3.0
  
  # Limits
  limits:
    max_images_per_halacha: 3
    max_images_per_chapter: 10
    max_images_per_episode: 20
  
  # Fallback behavior
  fallback:
    if_decision_fails: "skip"  # skip, generate_default, manual_review
    if_generation_fails: "retry_with_different_model"

# =============================================================================
# Prompt Configuration (Everything Configurable)
# =============================================================================
prompts:
  base_dir: "./prompts"
  
  # Override any prompt
  overrides:
    image_decision: "./prompts/custom/image_decision.yaml"
    diagram_generation: "./prompts/custom/diagram.yaml"
  
  # Template variables (user-defined)
  custom_variables:
    organization_name: "Merkos"
    target_audience: "adult learners"
    language_preference: "hebrew_primary"

# =============================================================================
# Text Alignment (More Configurability)
# =============================================================================
text_alignment:
  # Configurable passes
  passes:
    - name: "header_detection"
      enabled: true
      llm_model: "claude-haiku-3-5"  # Cheaper for simple task
      confidence_threshold: 0.7
      patterns:
        hebrew: ["הלכה", "פרק"]
        english: ["halacha", "chapter"]
        numeric: ["\\d+", "[א-י]+"]
    
    - name: "gap_detection"
      enabled: true
      llm_model: "claude-sonnet-4-20250514"
      detect_explicit_skips: true
      skip_markers: ["נדלג", "skip", "we'll come back"]
    
    - name: "content_matching"
      enabled: true
      llm_model: "claude-sonnet-4-20250514"
      use_semantic_similarity: true
      similarity_threshold: 0.75
      batch_size: 5  # Process 5 halachot at once
    
    - name: "verification"
      enabled: true
      llm_model: "claude-opus-4-20250514"  # Best model for verification
      require_manual_review_below: 0.6
  
  # Configurable edge case handling
  edge_cases:
    digression_detection:
      enabled: true
      markers: ["actually", "by the way", "let me tell you"]
      llm_model: "claude-haiku-3-5"
    
    reference_classification:
      enabled: true
      distinguish_primary_secondary: true
    
    reordering_detection:
      enabled: true
      track_pedagogical_order: true

# =============================================================================
# Telegram (More Configurability)
# =============================================================================
telegram:
  voting:
    # Configurable thresholds per class
    approval_thresholds:
      default: 0.70
      per_class:
        "cohen-shabbat": 0.75  # Higher standard
        "levy-shabbat": 0.65   # More lenient
    
    # Configurable voting window per priority
    voting_windows:
      high_priority: 12  # hours
      normal_priority: 24
      low_priority: 48
  
  edit_monitoring:
    # Configurable validation
    validation:
      quick_reject_patterns: ["^thanks?$", "^good$", "^nice$"]
      llm_model: "claude-haiku-3-5"
      confidence_threshold: 0.7
    
    # Configurable clarification
    clarification:
      enabled: true
      max_clarification_attempts: 2
      timeout_minutes: 30

# =============================================================================
# WhatsApp (More Configurability)
# =============================================================================
whatsapp:
  # Configurable message templates
  message_templates:
    default: "./templates/whatsapp_default.txt"
    per_class:
      "cohen-shabbat": "./templates/whatsapp_cohen.txt"
  
  # Configurable delivery schedule
  delivery_schedule:
    enabled: true
    preferred_times:
      - "08:00"  # Morning
      - "20:00"  # Evening
    timezone: "America/New_York"
    avoid_shabbat: true
    avoid_holidays: true
  
  # Configurable rate limiting per subscriber tier
  rate_limiting:
    default: 20  # messages per second
    premium: 50
    bulk: 10

# =============================================================================
# Cost Optimization (Configurable)
# =============================================================================
cost_optimization:
  # Model selection based on task complexity
  model_selection:
    simple_tasks:
      llm: "claude-haiku-3-5"
      cost_per_1k_tokens: 0.0008
    
    moderate_tasks:
      llm: "claude-sonnet-4-20250514"
      cost_per_1k_tokens: 0.003
    
    complex_tasks:
      llm: "claude-opus-4-20250514"
      cost_per_1k_tokens: 0.015
  
  # Configurable caching
  caching:
    sefaria_texts:
      enabled: true
      ttl_hours: 168  # 1 week
    
    alignment_results:
      enabled: true
      ttl_hours: 24
      cache_key_includes: ["transcript_hash", "sefaria_ref"]
    
    image_prompts:
      enabled: true
      ttl_hours: 72
      similarity_threshold: 0.9
  
  # Budget limits
  budget:
    daily_limit_usd: 50
    monthly_limit_usd: 1000
    alert_at_percentage: 80
    pause_at_percentage: 95

# =============================================================================
# Quality Assurance (Configurable)
# =============================================================================
quality:
  # Configurable metrics
  metrics:
    - name: "alignment_confidence"
      threshold: 0.7
      alert_below: true
    
    - name: "image_approval_rate"
      threshold: 0.5
      alert_below: true
      window_days: 7
    
    - name: "delivery_success_rate"
      threshold: 0.95
      alert_below: true
    
    - name: "cost_per_episode"
      threshold: 5.0
      alert_above: true
  
  # Configurable alerting
  alerting:
    channels:
      - type: "telegram"
        chat_id: "-1001234567890"
      - type: "email"
        address: "admin@example.com"
      - type: "slack"
        webhook_url: "https://hooks.slack.com/..."
    
    severity_levels:
      critical: ["alignment_confidence", "delivery_success_rate"]
      warning: ["image_approval_rate", "cost_per_episode"]
      info: ["processing_time"]

# =============================================================================
# Feature Flags (Ultimate Configurability)
# =============================================================================
features:
  dual_transcription: true
  sefaria_alignment: true
  image_decision_llm: true
  telegram_voting: true
  telegram_editing: true
  whatsapp_distribution: true
  reputation_system: false  # Disabled per user request
  cost_tracking: true
  quality_metrics: true
  retention_policies: true
  
  # Experimental features
  experimental:
    cross_class_image_reuse: false
    automatic_chapter_name_correction: false
    predictive_halacha_detection: false
```

---

## Implementation: Image Decision Maker

```python
class ImageDecisionMaker:
    """
    LLM-powered decision maker for image generation
    """
    
    def __init__(self, cfg: dict):
        self.cfg = cfg['image_generation']['decision']
        self.limits = cfg['image_generation']['limits']
        self.prompts = load_prompts()
        self.llm = self._get_llm()
    
    def decide_for_halacha(self, halacha_data: dict) -> list[ImageSpec]:
        """
        Decide if and how many images to generate for this halacha
        """
        
        # Check overrides
        if self._should_skip(halacha_data):
            return []
        
        if self._should_force_generate(halacha_data):
            return [self._default_image_spec(halacha_data)]
        
        # LLM decision
        prompt = self._build_prompt(halacha_data)
        response = self.llm.call(prompt)
        specs = self._parse_response(response)
        
        # Apply limits
        specs = self._apply_limits(specs, halacha_data)
        
        # Store decision
        self._store_decision(halacha_data, specs)
        
        return specs
    
    def _should_skip(self, halacha_data: dict) -> bool:
        """Check if generation should be skipped"""
        if self.cfg.get('skip_generation'):
            return True
        
        class_id = halacha_data.get('class_id')
        class_override = self.cfg.get('class_overrides', {}).get(class_id, {})
        
        return class_override.get('skip_generation', False)
    
    def _should_force_generate(self, halacha_data: dict) -> bool:
        """Check if generation should be forced"""
        if self.cfg.get('force_generate_all'):
            return True
        
        class_id = halacha_data.get('class_id')
        class_override = self.cfg.get('class_overrides', {}).get(class_id, {})
        
        return class_override.get('force_generate_all', False)
    
    def _apply_limits(self, specs: list, halacha_data: dict) -> list:
        """Apply configured limits"""
        max_per_halacha = self.limits['max_images_per_halacha']
        
        # Sort by priority
        specs = sorted(specs, key=lambda s: {
            'high': 0, 'medium': 1, 'low': 2
        }.get(s['priority'], 3))
        
        # Limit count
        return specs[:max_per_halacha]
    
    def _store_decision(self, halacha_data: dict, specs: list):
        """Store decision in database"""
        with self.db._connect() as conn:
            conn.execute(
                "INSERT INTO image_generation_decisions "
                "(chapter_id, halacha_num, should_generate, image_count, decision_reason) "
                "VALUES (?, ?, ?, ?, ?)",
                (halacha_data['chapter_id'], halacha_data['halacha_num'],
                 len(specs) > 0, len(specs),
                 specs[0]['reason'] if specs else 'No image needed')
            )
```

---

## Prompt Examples by Image Type

### Diagram System Prompt

```yaml
# prompts/diagram_system_prompt.yaml
system: |
  You are a technical illustrator specializing in educational diagrams.
  
  Your diagrams must be:
  - Clear and unambiguous
  - Labeled with Hebrew text (if needed)
  - Use arrows to show relationships
  - Simple color coding (max 3-4 colors)
  - Clean, minimalist style
  - Focus on structure and relationships
  
  Avoid:
  - Decorative elements
  - Complex shading
  - Photorealistic rendering
  - Cluttered layouts
```

### Infographic System Prompt

```yaml
# prompts/infographic_system_prompt.yaml
system: |
  You are an infographic designer for educational content.
  
  Your infographics must be:
  - Vertically oriented (portrait)
  - Organized in clear sections
  - Use icons and symbols
  - Include numbered steps if sequential
  - Balanced composition
  - Professional and clean
  
  Layout structure:
  - Title at top
  - Main content in middle (3-5 sections)
  - Summary or key point at bottom
```

### Chart System Prompt

```yaml
# prompts/chart_system_prompt.yaml
system: |
  You are a data visualization specialist.
  
  Your charts must be:
  - Clear comparison of concepts
  - Use visual hierarchy
  - Include legend if needed
  - Consistent color coding
  - Easy to read at a glance
  
  Chart types:
  - Comparison: Side-by-side elements
  - Hierarchy: Tree or pyramid structure
  - Flow: Process or decision flow
```

---

## CLI Commands

```bash
# Test image decision
python main.py test-image-decision <chapter_id> <halacha_num>

# Override decision
python main.py force-generate-image <chapter_id> <halacha_num> --type diagram

# Skip image generation
python main.py skip-image <chapter_id> <halacha_num>

# List all decisions for episode
python main.py list-image-decisions <episode_guid>

# Regenerate with different type
python main.py regenerate-image <image_version_id> --type infographic
```

---

## Summary of Changes

### Removed:
- Reputation system (not needed for 5 volunteers)
- Weighted chapter images (wrong abstraction - work at halacha level)

### Added:
- LLM-based image decision system (per halacha)
- Image type classification (illustration, diagram, infographic, chart, timeline, map)
- Per-type configuration (models, prompts, parameters)
- Maximum configurability throughout
- Feature flags for easy enable/disable

### Key Principles:
1. **LLM decides** if image is needed for each halacha
2. **LLM decides** how many images (0-3 per halacha)
3. **LLM decides** what type of image
4. **Everything is configurable** - no hardcoded values
5. **Per-class overrides** for flexibility
6. **Image types** tracked in database


---

## 🎨 Image Prompt Context Strategy

### Context Modes for Image Generation

**Problem:** How much context should we send to the image prompt generator LLM?

**Solution:** Configurable context modes with different information density levels.

---

### Context Mode: FULL

**Description:** Send all available content about the chapter/halacha

**Includes:**
- Original Hebrew text from Sefaria (all halachot in chapter)
- Transcripts from ALL classes covering this chapter
  - Rabbi Cohen's explanation
  - Rabbi Levy's explanation
  - Any other teachers
- Teacher-specific emphasis and interpretations
- Cross-references and comparisons
- Full alignment data with timestamps

**Use Case:**
- When you want maximum context for the image generator
- When multiple perspectives enrich the visual
- When chapter has complex multi-faceted concepts

**Pros:**
- Most comprehensive understanding
- Can synthesize multiple teaching approaches
- Rich detail for complex topics

**Cons:**
- Large token usage (expensive)
- May overwhelm the image generator
- Slower processing
- Risk of conflicting interpretations

**Example Prompt Structure:**
```
Chapter: Mishneh Torah, Shabbat 3

Original Hebrew Text (Sefaria):
[Full Hebrew text of all halachot in chapter 3]

Rabbi Cohen's Class (Episode 45, 12:30-25:00):
[Full transcript segment covering this chapter]
Key points: [extracted themes]

Rabbi Levy's Class (Episode 23, 5:00-18:00):
[Full transcript segment covering this chapter]
Key points: [extracted themes]

Cross-class synthesis:
- Both emphasize: [common themes]
- Cohen focuses on: [unique aspects]
- Levy focuses on: [unique aspects]

Generate image prompt for this chapter...
```

---

### Context Mode: SYNTHESIZED

**Description:** AI-generated standalone synopsis with essential background

**Process:**
1. Gather all available content (same as FULL mode)
2. Run dedicated LLM pass to synthesize into concise summary
3. Extract key visual concepts
4. Remove redundancy and tangential information
5. Focus on what's visually representable

**Includes:**
- Concise summary of chapter's main concept
- Key visual elements (measurements, sequences, comparisons)
- Essential background for understanding
- Synthesized themes across all classes
- Visual metaphors and symbolic representations

**Use Case:**
- Default mode for most chapters
- When cost optimization is important
- When chapter concept is straightforward
- When multiple classes say similar things

**Pros:**
- Optimized token usage (cost-effective)
- Focused on visual elements
- Removes noise and redundancy
- Faster processing
- Consistent quality

**Cons:**
- May lose nuance
- Synthesis step adds complexity
- Requires good synthesis prompt

**Example Prompt Structure:**
```
Chapter: Mishneh Torah, Shabbat 3

Synthesized Summary:
This chapter discusses the prohibition of carrying objects between domains on Shabbat. 
The key concept is the distinction between four domains: private, public, exempt, and 
open areas. The visual focus should be on spatial relationships and boundaries.

Key Visual Elements:
- Four distinct spatial zones
- Boundaries and transitions
- Objects being transferred
- Symbolic representation of prohibition

Essential Context:
Multiple teachers emphasize that this is fundamentally about awareness of boundaries 
and intentionality in actions. The measurement of "four cubits" is significant.

Visual Metaphors:
- Boundaries as thresholds
- Domains as distinct colored zones
- Movement as arrows (prohibited vs. permitted)

Generate image prompt for this chapter...
```

---

### Synthesis Prompt Template

**New prompt needed: `prompts.yaml`**

```yaml
context_synthesis:
  system: |
    You are a content synthesizer for visual educational materials.
    
    Your job: Take comprehensive source material and distill it into a concise 
    synopsis optimized for image generation.
    
    Focus on:
    - Visual concepts (spatial, temporal, comparative)
    - Key themes that can be represented symbolically
    - Essential background for understanding
    - Removing redundancy across multiple sources
    
    Avoid:
    - Purely textual/legal concepts with no visual component
    - Tangential stories or digressions
    - Repetitive information
    - Teacher-specific anecdotes
  
  user: |
    Synthesize the following content for image generation:
    
    Chapter: {chapter_ref}
    
    Original Hebrew Text:
    {hebrew_text}
    
    Class Transcripts:
    {all_class_transcripts}
    
    ---
    
    Create a synthesis optimized for image prompt generation.
    
    Return JSON:
    {{
      "main_concept": "One-sentence core concept",
      "visual_elements": ["element1", "element2", "element3"],
      "essential_context": "2-3 sentences of necessary background",
      "visual_metaphors": ["metaphor1", "metaphor2"],
      "spatial_concepts": ["if applicable"],
      "temporal_concepts": ["if applicable"],
      "comparative_concepts": ["if applicable"],
      "recommended_image_type": "illustration|diagram|infographic|chart"
    }}
```

---

### Configuration

**Add to `config.yaml`:**

```yaml
image_generation:
  # Context strategy for image prompt generation
  context_strategy:
    mode: "synthesized"  # "full" | "synthesized"
    
    # Per-class override
    per_class:
      "cohen-shabbat": "synthesized"
      "levy-shabbat": "full"  # Rabbi Levy's unique perspective warrants full context
    
    # Synthesis configuration (when mode = "synthesized")
    synthesis:
      llm:
        provider: "anthropic"
        model: "claude-sonnet-4-20250514"  # Good balance of cost/quality
      
      max_output_tokens: 1000  # Limit synthesis length
      
      # What to include in synthesis
      include:
        hebrew_text: true
        all_class_transcripts: true
        cross_class_comparison: true
        visual_metaphors: true
      
      # Cache synthesis results
      cache:
        enabled: true
        ttl_hours: 168  # 1 week
        cache_key: ["chapter_ref", "class_ids", "content_hash"]
    
    # Full mode configuration
    full:
      # Limit to prevent token overflow
      max_classes_included: 5
      max_transcript_length_per_class: 5000  # characters
      
      # Prioritize which classes to include if limit exceeded
      prioritization: "by_coverage_duration"  # "by_coverage_duration" | "by_teacher_priority" | "most_recent"
```

---

### Database Schema Addition

**Track which context mode was used:**

```sql
ALTER TABLE image_versions ADD COLUMN context_mode TEXT;
ALTER TABLE image_versions ADD COLUMN context_synthesis_id INTEGER;

-- Store synthesis results for reuse
CREATE TABLE context_syntheses (
    id SERIAL PRIMARY KEY,
    chapter_ref TEXT NOT NULL,
    class_ids INTEGER[] NOT NULL,
    content_hash TEXT NOT NULL,  -- Hash of input content
    
    -- Synthesis output
    main_concept TEXT,
    visual_elements JSONB,
    essential_context TEXT,
    visual_metaphors JSONB,
    spatial_concepts JSONB,
    temporal_concepts JSONB,
    comparative_concepts JSONB,
    recommended_image_type TEXT,
    
    -- Metadata
    synthesis_prompt TEXT,
    llm_model TEXT,
    synthesized_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(chapter_ref, content_hash)
);
```

---

### Implementation

**New file: `src/context_synthesizer.py`**

```python
class ContextSynthesizer:
    """
    Synthesize comprehensive content into concise image-generation-optimized summary
    """
    
    def __init__(self, cfg: dict):
        self.cfg = cfg['image_generation']['context_strategy']['synthesis']
        self.prompts = load_prompts()
        self.llm = self._get_llm()
        self.cache = self._get_cache()
    
    def synthesize(self, chapter_data: dict) -> dict:
        """
        Args:
            chapter_data: {
                'chapter_ref': 'Mishneh Torah, Shabbat 3',
                'hebrew_text': '...',
                'class_transcripts': [
                    {'class_id': 'cohen-shabbat', 'transcript': '...', 'duration_ms': 750000},
                    {'class_id': 'levy-shabbat', 'transcript': '...', 'duration_ms': 600000}
                ],
                'alignments': [...]
            }
        
        Returns:
            {
                'main_concept': '...',
                'visual_elements': [...],
                'essential_context': '...',
                'visual_metaphors': [...],
                'recommended_image_type': 'diagram'
            }
        """
        
        # Check cache
        cache_key = self._generate_cache_key(chapter_data)
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Build synthesis prompt
        prompt = self._build_synthesis_prompt(chapter_data)
        
        # Call LLM
        response = self.llm.call(prompt)
        synthesis = json.loads(response)
        
        # Store in cache and database
        self.cache.set(cache_key, synthesis)
        self._store_synthesis(chapter_data, synthesis)
        
        return synthesis
    
    def _generate_cache_key(self, chapter_data: dict) -> str:
        """Generate cache key from chapter ref and content hash"""
        content = json.dumps({
            'hebrew': chapter_data['hebrew_text'],
            'transcripts': [t['transcript'] for t in chapter_data['class_transcripts']]
        }, sort_keys=True)
        
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{chapter_data['chapter_ref']}:{content_hash}"
```

**Update: `src/image_prompt_generator.py`**

```python
class ImagePromptGenerator:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.context_mode = cfg['image_generation']['context_strategy']['mode']
        self.synthesizer = ContextSynthesizer(cfg) if self.context_mode == 'synthesized' else None
    
    def generate(self, chapter: Chapter, episode: Episode, all_class_data: dict) -> str:
        """
        Generate image prompt with configurable context strategy
        """
        
        # Determine context mode (check per-class override)
        mode = self._get_context_mode(episode.class_id)
        
        if mode == 'full':
            context = self._build_full_context(chapter, all_class_data)
        else:  # synthesized
            context = self._build_synthesized_context(chapter, all_class_data)
        
        # Generate image prompt using context
        prompt = self._generate_prompt_from_context(context, chapter)
        
        return prompt
    
    def _build_full_context(self, chapter, all_class_data):
        """Build comprehensive context with all available information"""
        return {
            'hebrew_text': all_class_data['sefaria_text'],
            'all_transcripts': all_class_data['class_transcripts'],
            'cross_class_synthesis': self._synthesize_cross_class(all_class_data),
            'mode': 'full'
        }
    
    def _build_synthesized_context(self, chapter, all_class_data):
        """Build synthesized context optimized for image generation"""
        synthesis = self.synthesizer.synthesize({
            'chapter_ref': chapter.sefaria_ref,
            'hebrew_text': all_class_data['sefaria_text'],
            'class_transcripts': all_class_data['class_transcripts'],
            'alignments': all_class_data['alignments']
        })
        
        return {
            'synthesis': synthesis,
            'mode': 'synthesized'
        }
```

---

### Cost Comparison

**Example: Chapter with 3 classes covering it**

**FULL Mode:**
- Hebrew text: ~2,000 tokens
- Class 1 transcript: ~3,000 tokens
- Class 2 transcript: ~2,500 tokens
- Class 3 transcript: ~2,800 tokens
- Cross-class synthesis: ~500 tokens
- **Total input: ~10,800 tokens**
- Cost: ~$0.03 per image prompt generation

**SYNTHESIZED Mode:**
- Synthesis step: 10,800 input tokens → 1,000 output tokens (~$0.04)
- Image prompt generation: 1,000 input tokens (~$0.003)
- **Total: ~$0.043 per image**
- But synthesis is cached! Subsequent images from same chapter: ~$0.003

**Savings with SYNTHESIZED:**
- First image: Similar cost (synthesis overhead)
- 2nd+ images from same chapter: 90% cost reduction
- If 3 classes cover same chapter → 3 images → 60% total cost reduction

---

### CLI Commands

```bash
# Test synthesis
python main.py test-synthesis <chapter_ref>

# Compare context modes
python main.py compare-context-modes <chapter_ref> --show-diff

# Regenerate with different context mode
python main.py regenerate-image <image_id> --context-mode full

# Clear synthesis cache
python main.py clear-synthesis-cache

# Show synthesis for chapter
python main.py show-synthesis <chapter_ref>
```

---

### Future Extensions

**Additional Context Modes (Extensible):**

1. **MINIMAL** - Only Hebrew text, no transcripts
2. **SINGLE_CLASS** - One class only (for class-specific images)
3. **COMPARATIVE** - Emphasize differences between classes
4. **VISUAL_ONLY** - Extract only visual concepts, ignore textual explanations
5. **CUSTOM** - User-defined context selection

**Configuration for extensibility:**

```yaml
image_generation:
  context_strategy:
    # Allow custom modes
    custom_modes:
      visual_focused:
        include:
          hebrew_text: false
          transcripts: true
          visual_elements_only: true
        synthesis_prompt_override: "./prompts/visual_synthesis.yaml"
```

---

### Summary

**Two primary modes:**
1. **FULL** - All content (expensive, comprehensive)
2. **SYNTHESIZED** - AI-generated synopsis (cost-effective, focused)

**Key benefits:**
- Configurable per-class
- Synthesis cached for reuse
- Optimized for image generation
- Extensible for future modes
- Significant cost savings with SYNTHESIZED mode

**Recommendation:** Use SYNTHESIZED as default, FULL for complex chapters or when multiple perspectives are essential.
