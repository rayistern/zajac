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
- Find spoken headers in transcript
- Patterns: "halacha 9", "halacha ט", "הלכה ט"
- Support Hebrew and English numbers
- Extract timestamps for each header
- Hebrew number mapping: א=1, ב=2, ג=3, etc.

#### Pass 2: Gap Detection
- Compare detected headers to source text
- Find missing halachot (e.g., 8 → 10, missing 9)
- Identify surrounding headers for context
- Prepare for content-based inference

#### Pass 3: Content Matching (LLM)
- Split transcript into segments based on headers
- Use LLM to match segments to source halachot
- Semantic content matching
- Return confidence scores
- Handle gaps using content similarity

#### Pass 4: Verification (LLM)
- Verify each alignment
- LLM checks if transcript matches source
- Approve/reject alignments
- Suggest adjustments to boundaries
- Final confidence scoring

**Output:**
```python
[{
    'transcript_segment': {...},
    'source_ref': 'Mishneh Torah, Shabbat 1:5',
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
5. Split into chapters (existing, but now based on alignments)
6. Generate images (existing)
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
- Pass 1: Detect spoken headers
- Pass 2: Find gaps in coverage
- Pass 3: Match content with LLM
- Pass 4: Verify alignments with LLM

### 5. Chapter Splitting
- Use alignments to create chapters
- Each chapter = one halacha or section
- Include timestamps for video overlay

### 6. Image Generation
- Generate image per chapter
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
