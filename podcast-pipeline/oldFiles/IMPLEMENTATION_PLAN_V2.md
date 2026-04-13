# 🎯 Implementation Plan V2 (Updated with Deep Analysis)

## Changes from V1

1. **Image prompt generation** - System prompts instead of string concatenation
2. **Sefaria name resolution** - MCP integration with disambiguation
3. **Weighted chapter images** - Based on time spent, not just presence
4. **Edit request validation** - Multi-stage with clarification
5. **Cost optimization** - Aggressive caching and smart provider selection
6. **Quality metrics** - Comprehensive monitoring and alerting
7. **Retention policies** - Data lifecycle management
8. **Reputation system** - Weighted voting to prevent gaming

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
# Chapter Image Generation
# ---------------------------------------------------------------------------
image_generation:
  strategy: "weighted_by_duration"  # vs "one_per_chapter", "one_per_halacha"
  
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

### 2.2: Weighted Chapter Image Generator

**File: `src/weighted_image_generator.py`**

```python
class WeightedImageGenerator:
    def generate_chapter_images(self, episode, alignments):
        """
        Generate images based on time spent per chapter
        """
        # Group by chapter
        by_chapter = self._group_by_chapter(alignments)
        
        # Calculate weights
        weights = self._calculate_weights(by_chapter)
        
        # Generate images with appropriate detail level
        images = []
        for chapter, aligns in by_chapter.items():
            weight = weights[chapter]
            
            # Determine detail level based on weight
            if weight > 0.5:
                detail = "high"
            elif weight > 0.2:
                detail = "medium"
            else:
                detail = "low"
            
            image = self._generate_image(
                chapter=chapter,
                alignments=aligns,
                weight=weight,
                detail_level=detail
            )
            images.append(image)
        
        return images
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

### 2.4: Reputation Manager

**File: `src/reputation_manager.py`**

```python
class ReputationManager:
    def update_reputation(self, user_id):
        """
        Update reputation based on:
        - Agreement with consensus
        - Voting consistency
        - Participation rate
        """
        
    def get_weighted_votes(self, telegram_message_id):
        """
        Weight votes by reputation
        """
        votes = self.db.get_votes(telegram_message_id)
        reputations = self.db.get_reputations([v.user_id for v in votes])
        
        weighted_upvotes = sum(
            r.score for v, r in zip(votes, reputations)
            if v.vote_type == 'upvote'
        )
        
        weighted_downvotes = sum(
            r.score for v, r in zip(votes, reputations)
            if v.vote_type == 'downvote'
        )
        
        return weighted_upvotes, weighted_downvotes
```

### 2.5: Cost Tracker

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

### 2.6: Quality Metrics Tracker

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

### 2.7: Retention Manager

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
