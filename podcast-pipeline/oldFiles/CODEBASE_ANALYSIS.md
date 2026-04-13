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

### 1. Chapter Splitting Strategy Conflict ⚠️

**Current Implementation:**
```yaml
chapters:
  strategy: "both"  # provider first, fallback to llm
```

**Problem:**
- The current chapter splitter uses transcription provider chapters (AssemblyAI auto-chapters)
- This is designed for English podcasts with natural topic breaks
- **Conflicts with Rambam alignment approach** where chapters = halachot from Sefaria
- The "both" strategy will try to use AssemblyAI chapters first, which won't align with Rambam structure

**Solution:**
- Replace chapter splitting entirely with **Sefaria-based alignment**
- Chapters should be determined by:
  1. Detected halacha headers in transcript
  2. Content matching to Sefaria halachot
  3. NOT by transcription provider's auto-chapters
- Remove or deprecate the "provider" and "both" strategies
- Keep "llm" strategy only as fallback for non-Rambam content

**Required Changes:**
- Update `chapter_splitter.py` to support "sefaria_alignment" strategy
- Make text alignment the PRIMARY chapter splitting method
- Deprecate provider-based chapter detection for this use case

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

### 3. No Chapter Coverage Tracking ⚠️

**Current Implementation:**
- No tracking of which Rambam chapters/halachot are covered
- No way to know "Rabbi Cohen is on Chapter 3, Halacha 5"
- No cross-class comparison

**Solution:**
- Add `class_progress` table
- Track chapter/halacha coverage per class
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

### 4. No Chapter Name Standardization ⚠️

**Current Implementation:**
- Chapter titles come from LLM or transcription provider
- No normalization to Sefaria format
- Teacher might say "Shabbos" vs "Shabbat", "Hilchos" vs "Hilchot"

**Problem:**
- Inconsistent chapter names across classes
- Can't easily match to Sefaria references
- Hard to compare coverage

**Solution:**
- Add LLM pass to standardize chapter names
- Map detected names to canonical Sefaria format
- Store both original and standardized names

**Implementation:**
```python
class ChapterNameStandardizer:
    def standardize(self, detected_name: str, context: str) -> dict:
        """
        Use LLM to map detected chapter name to Sefaria format
        
        Input: "Hilchos Shabbos Chapter 3"
        Output: {
            "original": "Hilchos Shabbos Chapter 3",
            "standardized": "Mishneh Torah, Shabbat 3",
            "sefaria_ref": "Mishneh Torah, Shabbat 3",
            "confidence": 0.95
        }
        """
```

**Database Schema Addition:**
```sql
ALTER TABLE text_alignments ADD COLUMN original_chapter_name TEXT;
ALTER TABLE text_alignments ADD COLUMN standardized_chapter_name TEXT;
ALTER TABLE text_alignments ADD COLUMN name_standardization_confidence FLOAT;
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

### 7. Episode-Chapter Relationship Issue ⚠️

**Current Implementation:**
```python
# One episode = multiple chapters
# But chapters are auto-generated, not aligned to Rambam
```

**Problem:**
- Current model assumes chapters are subdivisions of episodes
- In reality: **One class episode can span multiple Rambam chapters**
- Example: 45-minute class might cover Shabbat 2:5 through 3:8
- Need to track: Episode → Multiple Rambam Chapters/Halachot

**Solution:**
- Decouple chapters from episodes
- Use alignment data to determine coverage
- One episode can map to many halachot across multiple chapters

**Updated Data Model:**
```
Episode (45 min class)
  ├─ Alignment 1: Shabbat 2:5 (0:00-5:30)
  ├─ Alignment 2: Shabbat 2:6 (5:30-12:00)
  ├─ Alignment 3: Shabbat 2:7 (12:00-18:45)
  ├─ Alignment 4: Shabbat 3:1 (18:45-25:00)  ← Crosses chapter boundary!
  └─ Alignment 5: Shabbat 3:2 (25:00-45:00)

Images Generated:
  - One image per Rambam chapter covered
  - Shabbat Chapter 2 (composite of halachot 5-7)
  - Shabbat Chapter 3 (composite of halachot 1-2)
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
4. Align transcript to Sefaria (4-pass LLM)
5. Standardize chapter names (LLM)
6. Group alignments by Rambam chapter
7. Generate ONE image per Rambam chapter (not per halacha)
8. Post to Telegram voting group
9. Monitor for edit requests
10. Generate new versions on request
11. Tally votes when window expires
12. Blast approved images to WhatsApp
```

### 2. Chapter Splitting Replacement

**Remove:**
- `chapter_splitter.py` (or heavily modify)
- Provider-based chapter detection
- LLM-based topic splitting

**Replace with:**
- `text_aligner.py` (already planned)
- Sefaria-based chapter determination
- Halacha-level granularity with chapter-level grouping

### 3. Image Generation Strategy

**Current:** One image per chapter (auto-detected)

**New:** One image per Rambam chapter covered in episode

**Implementation:**
```python
def generate_chapter_images(episode, alignments):
    """
    Group alignments by Rambam chapter
    Generate one image per chapter
    Image represents the entire chapter's content from this episode
    """
    
    # Group by chapter
    by_chapter = {}
    for alignment in alignments:
        chapter_num = alignment['chapter_num']
        if chapter_num not in by_chapter:
            by_chapter[chapter_num] = []
        by_chapter[chapter_num].append(alignment)
    
    # Generate one image per chapter
    images = []
    for chapter_num, chapter_alignments in by_chapter.items():
        # Combine all halachot summaries for this chapter
        combined_summary = combine_halachot(chapter_alignments)
        
        # Generate image for entire chapter
        image = generate_image(
            chapter_num=chapter_num,
            summary=combined_summary,
            halachot_covered=[a['halacha_num'] for a in chapter_alignments]
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
  strategy: "sefaria_alignment"  # Primary method
  fallback_strategy: "llm"  # Only for non-Rambam content
  
  # Chapter name standardization
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
  grouping_strategy: "by_rambam_chapter"  # vs "by_halacha"
  
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
    You create image prompts for Rambam chapters based on multiple halachot.
  
  user: |
    Create an image for Mishneh Torah, {book_name}, Chapter {chapter_num}.
    
    This episode covered halachot {halacha_range}.
    
    Combined summary:
    {combined_summary}
    
    Key themes: {themes}
    
    Generate ONE cohesive image prompt that represents this chapter.
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

2. **`src/chapter_name_standardizer.py`** - Standardize chapter names
```python
class ChapterNameStandardizer:
    def standardize(self, detected_name: str, context: str) -> dict
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
   - Replace chapter splitting with alignment
   - Add chapter name standardization
   - Add image versioning
   - Add edit monitoring

2. **`src/chapter_splitter.py`**
   - Deprecate provider/both strategies
   - Add sefaria_alignment strategy
   - Or replace entirely with text_aligner.py

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

# Chapter name standardization
python main.py standardize-chapter-name "Hilchos Shabbos 3"
python main.py validate-sefaria-ref "Mishneh Torah, Shabbat 3"

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

2. **Chapter name standardization**
   - Test various input formats
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
   - Episode covering Shabbat 2:8 through 3:5
   - Verify correct chapter grouping
   - Check image generation per chapter

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

### Phase 3: Chapter Name Standardization (Week 2)
1. Implement ChapterNameStandardizer
2. Add prompts
3. Integrate into alignment pipeline
4. Test with various input formats

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
- `chapters.strategy: "both"` → `chapters.strategy: "sefaria_alignment"`

### Database Schema
- `episodes` table needs `class_id` column
- `chapters` table structure changes significantly
- New tables: classes, class_progress, image_versions, image_edit_conversations

### API Changes
- `Pipeline.run()` needs class_id parameter
- `ChapterSplitter.split()` signature changes
- Image generation returns version_id not just path

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

2. **Multi-Class Guide**
   - How to set up multiple classes
   - How to track progress
   - How to compare coverage

3. **Image Editing Guide**
   - How volunteers request edits
   - What makes a valid edit request
   - How to manage versions

4. **Sefaria Integration Guide**
   - How chapter alignment works
   - How to configure Sefaria references
   - Troubleshooting alignment issues

---

## Open Questions

1. **Image Generation Granularity**
   - One image per Rambam chapter? (Recommended)
   - Or one image per halacha? (Too many images)
   - Or one image per episode? (Too coarse)

2. **Edit Request Approval**
   - Should edits require approval before generation?
   - Or generate immediately and let voting decide?

3. **Cross-Chapter Episodes**
   - If episode covers chapters 2-4, generate 3 images?
   - Or one composite image?

4. **Chapter Name Conflicts**
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
| Chapter name standardization | 2 days | P0 |
| Replace chapter splitting | 3 days | P0 |
| Image versioning | 2 days | P1 |
| Edit workflow | 4 days | P1 |
| Testing & integration | 3 days | P0 |
| Documentation | 2 days | P1 |
| **Total** | **21 days** | |

---

## Conclusion

The current codebase has a solid foundation but requires significant architectural changes to support:
- Multiple classes/teachers
- Rambam-aligned chapter detection
- Interactive image editing
- Version management

The biggest change is replacing the generic "chapter splitting" approach with a Sefaria-aligned, halacha-based system. This fundamentally changes how the pipeline works but aligns perfectly with the use case of processing Torah classes.

**Recommendation:** Proceed with clean break migration, implement in phases, prioritize core functionality (multi-class + alignment) before advanced features (editing).
