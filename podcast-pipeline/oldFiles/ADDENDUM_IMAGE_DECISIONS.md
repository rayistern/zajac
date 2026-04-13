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
- Weighted chapter images (pushed to future)

### Added:
- LLM-based image decision system
- Image type classification (illustration, diagram, infographic, chart, timeline, map)
- Per-type configuration (models, prompts, parameters)
- Maximum configurability throughout
- Feature flags for easy enable/disable

### Key Principles:
1. **LLM decides** if image is needed
2. **LLM decides** how many images (0-3 per halacha)
3. **LLM decides** what type of image
4. **Everything is configurable** - no hardcoded values
5. **Per-class overrides** for flexibility
6. **Image types** tracked in database
