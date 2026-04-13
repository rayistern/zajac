# Merkos Rambam — Final Product Specification & Build Plan

| | |
|---|---|
| **Product** | Merkos Rambam Learning Platform |
| **Owner** | Rayi Stern |
| **Organization** | Merkos 302 / ChabadAI |
| **Date** | April 2026 |
| **Status** | Pre-Development — Consolidated Spec |

---

## 1. What This Is

Merkos Rambam is a mobile-first Progressive Web App that transforms the daily Rambam learning experience into an immersive, multimedia study session. It combines:

- **AI-generated visual content** (illustrations, diagrams, infographics, charts) synced to Torah audio classes
- **Sichos references** mapped at the individual halacha level
- **An immersive audio/video player** where artifacts, source text, and teacher audio move together in sync
- **A voice chatbot** ("Raise Hand") that lets learners ask questions mid-class, with full context of where they are in the shiur
- **A shareable content engine** producing branded, watermarked assets for WhatsApp and social media

The target audience is people who already learn Rambam daily (1-perek or 3-perek tracks), primarily within Chabad communities. Teachers/Maggidei Shiur are the highest-leverage distribution channel — they share assets to WhatsApp groups, putting content in front of large audiences with implicit endorsement.

---

## 2. Core Design Principles

1. **The content is the product.** The app is delivery infrastructure. Content quality determines success or failure.
2. **Narrow and deep over broad and shallow.** Serve daily Rambam learners exceptionally well before expanding.
3. **Every shareable asset works at two levels.** For a learner: comprehension aid. For a non-learner on social media: self-contained story.
4. **AI generates, humans validate.** No AI-generated Torah content publishes without human editorial review. No exceptions.
5. **Source of truth is Sefaria.** All content maps back to canonical text.
6. **Everything configurable.** No hardcoded thresholds, prompts, providers, or timings.
7. **Idempotent operations.** Every pipeline stage can be re-run without producing duplicates.

---

## 3. System Architecture

### 3.1 End-to-End Flow

```
RSS Feeds (multiple Torah classes)
    │
    ▼
Episode Download + Dual Transcription
  ├── sofer.ai (accurate Hebrew, no timestamps)
  └── Whisper (word-level timestamps)
    │
    ▼
Transcript Merge (accurate text + timestamps)
    │
    ▼
Sefaria Text Fetch (canonical Hebrew, canonical refs)
    │
    ▼
4-Pass LLM Alignment (transcript segments → source units/halachot)
    │
    ▼
Artifact Planning (LLM generates manifest per source unit)
    │
    ▼
Artifact Generation (images, charts, infographics, text)
    │
    ▼
Editorial Review (Telegram voting group + human approval)
    │
    ▼
Publication → Web Player + WhatsApp Distribution
```

### 3.2 Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | Next.js 14+ (App Router), TypeScript, Tailwind CSS + Radix UI | PWA support, SSR/SSG, RTL, accessible primitives |
| **Database** | Supabase (PostgreSQL) | Open source, managed, real-time, auth built-in |
| **File Storage** | Cloudflare R2 | S3-compatible, no egress fees, global CDN |
| **Cache** | Upstash Redis | Serverless, pay-per-request |
| **Hosting** | Vercel | Optimal Next.js support, edge functions |
| **LLM Routing** | PortKey → Anthropic Claude | Model flexibility, fallbacks, cost tracking |
| **Image Generation** | Replicate (Flux/SDXL) + DALL-E 3 | Open source models for illustrations, DALL-E for diagrams |
| **Transcription** | sofer.ai (primary) + Whisper (timestamps) | Best Hebrew accuracy + word-level timing |
| **Text Source** | Sefaria API | Canonical, open, halacha-level indexing |
| **WhatsApp** | Twilio WhatsApp Business API | Standard integration |
| **Analytics** | PostHog | Open source, privacy-focused |
| **Error Tracking** | Sentry | Industry standard |
| **Editorial** | Telegram voting group + Notion | Lightweight, adequate for Phase 1 volume |

### 3.3 Backend Pipeline (Python)

The content generation backend is a Python pipeline deployed on AWS (ECS Fargate, RDS PostgreSQL, S3, SQS, EventBridge). Key modules:

| Module | Purpose |
|--------|---------|
| `dual_transcriber.py` | Parallel sofer.ai + Whisper transcription, then merge |
| `sefaria_client.py` | Fetch and cache canonical texts |
| `text_aligner.py` | 4-pass LLM alignment (headers → gaps → content → verification) |
| `artifact_planner.py` | LLM plans what visual artifacts each halacha needs |
| `context_synthesizer.py` | Condenses context for image generation (FULL vs SYNTHESIZED modes) |
| `image_generator.py` | Executes planned artifacts with style rotation |
| `telegram_poster.py` | Posts to voting group for volunteer review |
| `vote_manager.py` | Tallies votes, manages approval thresholds |
| `whatsapp_sender.py` | Rate-limited distribution to subscribers |
| `reconciliation.py` | LLM audits artifact lifecycle for staleness/orphans |

---

## 4. Data Model

### 4.1 Core Entities

```
Works ──────────── Source Units (halachot/verses/mishnayot)
                        │
Classes ─── Episodes ───┤
                │       │
           Transcripts  Alignments (transcript → source unit mapping)
                        │
                   Artifact Plans
                        │
                   Artifacts ──── Artifact Versions
                        │              │
                   Vote Sessions ── Votes / Edit Requests
                        │
                   WhatsApp Deliveries
```

**Key design decisions:**
- **Generic artifact system.** `artifact_types` table supports image, video, text, interactive — new types require no schema changes.
- **Artifact lifecycle:** `planned → ordered → generated → in_review → approved → published → hidden` (or `rejected`)
- **Position float (0.0–1.0):** Places an artifact within a source unit for timeline display.
- **Artifact timeline view:** A DB view that computes `display_start_ms` and `display_end_ms` from alignment windows + position, so the frontend gets a complete playback timeline in one call.

### 4.2 Frontend Data Model (Supabase)

```sql
-- Learning schedule
learning_days (date, hebrew_date, track_1_perakim, track_3_perakim)

-- Content items (all generated content)
content_items (learning_day_id, content_type, sefer, perek, halacha_start,
               halacha_end, title, content JSONB, image_url, status,
               reviewed_by, generation_model)

-- Sichos mapping (structured data, not AI-generated)
sichos_references (sefer, perek, halacha, source_volume, source_page, excerpt)

-- User preferences (anonymous, privacy-respecting)
user_preferences (device_id, track)

-- WhatsApp subscribers
whatsapp_subscribers (phone_hash, track, status)
```

---

## 5. Frontend — The Immersive Player

### 5.1 Vision

Not a podcast player. Not a video player. Not a text study interface. All three unified — an **immersive content experience** where audio/video, generated artifacts, and source text move together in sync with the class.

The experience should feel like sitting in the shiur with a brilliant visual assistant who surfaces exactly the right thing at exactly the right moment.

### 5.2 Layout Zones

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│                  MAIN ZONE                          │
│   (video / artifact / dynamic content)              │
│                                                     │
│   [source text overlay — subtitle style, RTL]       │
│                                                     │
├───────────────────────┬─────────────────────────────┤
│                       │                             │
│   ARTIFACT TRAY       │   TEXT PANEL                │
│   (queue of upcoming  │   (Rambam source text,      │
│   artifacts: images,  │   active halacha            │
│   charts, etc.)       │   highlighted + scrolled)   │
│                       │                             │
├───────────────────────┴─────────────────────────────┤
│              PLAYBACK CONTROLS                      │
│   ◀◀  ▶  ▶▶   ────●──────────────   ✋ (chatbot)  │
└─────────────────────────────────────────────────────┘
```

### 5.3 Media Scenarios

| Scenario | Main Zone Behavior |
|----------|-------------------|
| **Audio only** (most current episodes) | Artifacts display on schedule; ambient visual when nothing active |
| **Video available** (talking head) | Video in Main Zone by default; when artifact scheduled, video moves to PiP |
| **Text only** (future) | Entirely artifact-driven |

### 5.4 Artifact Display Model

**Hybrid (recommended):** Default is passive auto-advance (artifacts appear/disappear on computed schedule). User can tap to pause an artifact (freeze it while audio continues) or dismiss early. Like pausing a slide while listening to the speaker.

| Artifact Type | Display Behavior |
|---------------|-----------------|
| `image / illustration` | Full Main Zone, displaces video to PiP |
| `image / diagram` | Full Main Zone or lower section |
| `image / infographic` | Full Main Zone, user may want to explore |
| `image / chart` | Lower section or full, depends on complexity |
| `image / timeline` | Full Main Zone, horizontal layout |
| `interactive` (future) | Full Main Zone, suspends auto-advance |

### 5.5 Source Text Overlay

The original canonical Hebrew text overlaid subtitle-style on the Main Zone, synced to playback via alignment timestamps. **Not the transcript** — the original Rambam text, surfaced at the moment the teacher discusses it.

- RTL, Hebrew font, right-aligned
- Fade in at `halacha_start_ms`, fade out at `halacha_end_ms`
- User-toggleable, configurable font size

### 5.6 Text Panel

Dedicated panel showing full Rambam source text. Active halacha highlighted and auto-scrolled. Surrounding halachot shown for context. Click any halacha to jump playback to that point.

- Desktop: expanded by default (right sidebar)
- Mobile: collapsed by default, tap to expand as bottom sheet

### 5.7 Mobile vs Desktop

| | Mobile | Desktop |
|---|--------|---------|
| Main Zone | Full width, dominant | Wider, all zones visible simultaneously |
| Text Panel | Collapsed, bottom sheet | Expanded sidebar |
| Artifact Tray | Horizontal scroll strip | Visible panel |
| Chatbot | Floating ✋ button | Sidebar or floating panel |
| Design priority | Consumption-first | Study-first |

### 5.8 Player View — Content Feed (Phase 1 Simplified)

Before the full immersive player, Phase 1 ships a simpler but still compelling experience:

- **Hero image:** Fills 60–70% of viewport on load. Collapses on scroll.
- **Content feed:** Vertical scroll of interleaved blocks — halacha text, illustrations, charts, infographics, sichos references. Content types flow naturally with zero friction.
- **Audio controls:** Fixed mini-bar at bottom (Spotify-style).
- **Raise Hand button:** Triggers voice AI conversation.

### 5.9 Additional Screens

- **Home / Content Discovery** — daily content, track selector
- **Perek Detail / Pre-play** — overview before diving in
- **Progress & Streaks** — engagement tracking
- **Raise Hand / Voice Conversation** — chatbot interface

---

## 6. Voice Chatbot ("Raise Hand") — Phase 3

### 6.1 Concept

User taps ✋ during playback. A voice interface opens. The chatbot knows exactly where in the class the user is — what halacha is being discussed, what the teacher just said, what artifacts have been shown. The user is **talking to the class**, not a generic AI.

### 6.2 Interaction Flow

1. User taps ✋
2. Playback optionally pauses (configurable)
3. Microphone opens — user speaks
4. Voice → text (Whisper STT)
5. Context package assembled (current timestamp, active halacha, last 10 min of transcript, artifacts shown so far)
6. LLM generates response (grounded in class content + source text)
7. Text → voice (TTS)
8. Response plays back
9. User can ask follow-up or dismiss
10. Playback resumes

### 6.3 Context Package

```
System prompt: You are a study assistant for this Torah class.
               Answer based on the class content and source text.
               Be concise — the response will be spoken aloud.

Context:
  Current timestamp, active source unit (Hebrew text + ref)
  Transcript up to this point (last 10 minutes, truncated)
  Halachot covered so far (with brief summaries)
  Artifacts shown so far

User question: {transcribed voice input}
```

The cutoff is the current playback timestamp — the chatbot only knows what has been said up to where the user is. No access to future content.

### 6.4 Logging

All chatbot interactions logged (`chatbot_sessions` table) for quality improvement: question text, response text, models used, context tokens, active source unit at time of query.

---

## 7. Content Types & Generation Pipelines

### 7.1 Content Types (Phase 1)

| Content Type | Description | Generation Method |
|-------------|-------------|-------------------|
| **Conceptual images** | AI illustrations of complex halachos | Image generation API + style guide + human selection |
| **Infographics** | Flowcharts, timelines, comparison tables | Same image pipeline, different prompt templates |
| **Daily charts** | Visual charts from day's content | Chart generation system |
| **Perek overviews** | AI orientation summary per perek | LLM from Rambam text |
| **"Did you know" insights** | Single compelling fact per day | LLM from Rambam text |
| **Sichos highlights** | Rebbe's sichos mapped to halachot | Automated footnote cross-referencing (not AI) |

### 7.2 Generation Pipelines

| Pipeline | Produces | Shared Infrastructure |
|----------|---------|----------------------|
| **Visual** | Conceptual images, infographics, charts | Image generation API, style system (5 styles with rotation), watermarking, visual review |
| **Text** | Perek overviews, "Did you know", quiz questions (Phase 1.5) | LLM via PortKey, prompt templates, text review |
| **Sichos** | Halacha-mapped sichos references | Structured data mapping (not AI) |
| **Retrieval** (Phase 2) | Cross-references, Chassidus connections | Vector DB, RAG |

### 7.3 Image Style System

Five named styles rotate randomly per image (configurable per class, overridable via Telegram):

- **Photorealistic** — cinematic lighting, rich textures, warm earth tones
- **Watercolor** — soft washes, flowing lines, spiritual atmosphere
- **Cartoon** — clean editorial style, bold outlines, flat fills
- **Line Art** — pen and ink, cross-hatching, scholarly quality
- **Oil Painting** — classical, Rembrandt-style lighting, impasto texture

All styles: no faces/human figures (Jewish artistic tradition), historically accurate, clearly labeled measurements, respectful of subject matter.

### 7.4 Content Accuracy & Editorial

- **All AI content reviewed before publication.** Non-negotiable.
- **7-day content buffer** ensures review is never rushed.
- **Minimum 3 reviewers per day** (6–10 volunteers needed for sustainable rotation).
- **Degradation policy:** 2 reviewers = publish with flag; 1 reviewer = text/sichos only, no AI visuals; 0 reviewers = Rambam text only, no AI content.
- **Chatbot** grounded exclusively in approved sources, with AI disclosure on every response and a kill switch.

---

## 8. Sharing & Distribution

### 8.1 Shareable Assets

Every content view generates a branded, watermarked card optimized for WhatsApp and social media. Generated on-demand via Next.js `ImageResponse` (OG image generation). Share cards include:

- Merkos Rambam branding + watermark
- Content preview (image, text excerpt, or infographic)
- QR/link back to the platform
- Self-contained — communicates the concept without requiring the app

### 8.2 WhatsApp Delivery

- Daily content package: featured image + text summary + link to platform
- Twilio WhatsApp Business API
- Rate-limited (20/sec), retry with exponential backoff
- Delivery tracking (queued → sent → delivered → read → failed)
- Per-class opt-in, immediate or scheduled blast timing

### 8.3 Distribution SLA

Content must be live before the earliest global sunset each day (Australia shkiah). Fridays: Shabbos content reviewed and queued by Thursday.

---

## 9. Phased Delivery Plan

### Phase 0 — Content Validation (Pre-App)
**Duration:** Days to weeks. **No application built.**

- Automated script generating candidate images for daily Rambam
- Human curation, daily distribution to 3–5 WhatsApp groups + 2–3 teachers
- **Transition criteria:** organic forwarding beyond seed groups, teacher adoption, inbound subscriber requests, feature requests for archive/website

### Phase 1 — Core Platform
**Timeline:** 1–2 weeks initial build.

- Daily homepage with halacha-indexed Rambam text
- Track selection (1-perek / 3-perek, persistent)
- Content feed: images, infographics, charts, overviews, sichos
- Shareable branded assets with watermarking
- WhatsApp daily delivery
- Simplified player (hero image + scrolling content feed + audio mini-bar)

### Phase 1.5 — Interaction Layer
**Triggered by:** Sustained daily usage, stable content pipeline.

- Voice chatbot ("Raise Hand") scoped to today's learning
- Quiz / review questions per perek
- Sefer Hamitzvos mapping
- Bookmarks / notes

### Phase 2 — Immersive Player
**Triggered by:** 1,000+ DAU sustained, 5,000+ WhatsApp subscribers, 50%+ 7-day retention.

- Full immersive player with Main Zone, Artifact Tray, Text Panel
- Audio/video + artifact sync with timeline-based display
- Source text overlay (subtitle-style, synced to playback)
- PiP for video when artifacts display
- Secondary/commentary texts (deferred within Phase 2)

### Phase 3 — Voice Chatbot (Full)
- Voice interaction integrated into immersive player
- Context-aware (knows exactly where user is in class)
- STT → LLM → TTS pipeline
- Conversation logging for quality improvement

### Future Directions (Not Committed)
- Per-halacha commentary extracted from shiurim
- Inline biurim, audio shiurim synced to text
- Multilingual support (Hebrew/English)
- Rabbi-facing CMS, embeddable widgets
- Rambam-to-Shulchan Aruch mapping
- Content API for third-party applications
- Spaced repetition, Chidon study mode
- Application to other daily learning programs

---

## 10. API Design

### 10.1 Public Endpoints (Phase 1)

```
GET  /api/content/today                     — Today's content for selected track
GET  /api/content/day/[date]                — Content for specific date
GET  /api/content/perek/[sefer]/[perek]     — Specific perek content
GET  /api/content/item/[id]                 — Individual content item
GET  /api/rambam/[sefer]/[perek]            — Full perek text (cached Sefaria proxy)
GET  /api/rambam/[sefer]/[perek]/[halacha]  — Individual halacha text
GET  /api/sichos/[sefer]/[perek]            — Sichos for a perek
GET  /api/share/[contentId]                 — Generate share card image
GET  /api/share/[contentId]/meta            — OG meta for share URLs
GET  /api/preferences                       — Get user preferences
PUT  /api/preferences                       — Update preferences
POST /api/webhook/whatsapp                  — Twilio webhook
POST /api/cron/generate                     — Trigger daily generation
POST /api/cron/publish                      — Trigger publication
```

### 10.2 Immersive Player Endpoints (Phase 2)

```
GET  /api/episode/:id/timeline              — Full artifact timeline + halachot + media
GET  /api/episode/:id/transcript            — Full transcript (client-side seeking)
GET  /api/classes                            — Class listing
GET  /api/class/:id/episodes                — Episodes for a class
```

### 10.3 Chatbot Endpoint (Phase 3)

```
POST /api/chatbot/query                     — Voice query (audio blob + episode_id + current_ms)
```

---

## 11. Frontend Application Structure

```
/app
├── (marketing)/
│   ├── page.tsx                — Landing page
│   └── about/page.tsx
├── (app)/
│   ├── layout.tsx              — App shell with track selector
│   ├── page.tsx                — Today's learning
│   ├── day/[date]/page.tsx     — Daily content view
│   ├── perek/[sefer]/[perek]/page.tsx  — Perek deep-dive
│   ├── player/[episodeId]/page.tsx     — Immersive player (Phase 2)
│   └── share/[contentId]/page.tsx      — Share card generator
├── api/                        — API routes (see §10)
├── globals.css
└── layout.tsx                  — Root layout (RTL, Hebrew fonts, providers)

/components
├── ui/                         — Radix-based primitives
├── content/
│   ├── RambamText.tsx          — Halacha-indexed text display
│   ├── ConceptualImage.tsx     — Image with caption
│   ├── Infographic.tsx         — Structured visual
│   ├── SichosHighlight.tsx     — Sichos reference card
│   ├── PerekOverview.tsx       — Summary component
│   ├── DailyChart.tsx          — Chart component
│   └── ShareCard.tsx           — Branded share card
├── player/
│   ├── MainZone.tsx            — Primary visual surface
│   ├── ArtifactTray.tsx        — Artifact queue/strip
│   ├── TextPanel.tsx           — Source text with active highlight
│   ├── SourceTextOverlay.tsx   — Subtitle-style Hebrew overlay
│   ├── PlaybackControls.tsx    — Transport + raise hand button
│   └── RaiseHand.tsx           — Voice chatbot interface
├── navigation/
│   ├── TrackSelector.tsx       — 1-perek / 3-perek toggle
│   ├── DayNavigator.tsx        — Previous / Next day
│   └── Header.tsx
└── share/
    └── ShareButton.tsx         — Multi-platform share

/lib
├── sefaria.ts                  — Sefaria API client
├── content.ts                  — Content fetching/caching
├── share.ts                    — Share URL generation
├── analytics.ts                — PostHog wrapper
├── cache.ts                    — Upstash Redis caching
├── offline.ts                  — Service worker / PWA offline
└── utils.ts

/hooks
├── useTrack.ts                 — Track preference (localStorage + cookie)
├── useHebrewDate.ts            — Hebrew date utilities
├── useLearningDay.ts           — Current day content
├── usePlayback.ts              — Audio/video playback state
└── useArtifactTimeline.ts      — Artifact display scheduling
```

---

## 12. Success Metrics

### Phase 0

| Signal | Green | Red |
|--------|-------|-----|
| Organic forwarding (Day 7) | Images in unseeded groups | No organic spread |
| Teacher adoption (Day 14) | Regular use in shiurim | No engagement |
| Inbound requests (Day 14) | Unprompted join requests | None |
| Feature requests (Day 30) | Archive, website, more context | Silence |

### Phase 1

| Metric | 30-Day | 90-Day | Phase 2 Trigger |
|--------|--------|--------|-----------------|
| Daily active users | 200+ | 500+ | 1,000+ sustained |
| WhatsApp subscribers | 500+ | 2,000+ | 5,000+ |
| Daily content shares | 20+ | 100+ | 300+ |
| 7-day retention | 25%+ | 40%+ | 50%+ |
| Content buffer depth | 3+ days | 7 days | 7 days sustained |
| Editorial pass rate | 90%+ | 95%+ | 98%+ |

### Discontinuation Criteria

- Phase 0: no forwarding/requests after 30 days → iterate content, don't build app
- Phase 1 DAU below 100 after 60 days → diagnose before further investment
- Volunteer editorial model fails (< 2 reviewers for 2+ weeks) → pause AI content
- Retention below 15% at 90 days → resolve UX/content failure before Phase 2

---

## 13. Key Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| AI generates halachically inaccurate content | Critical | Human review on all content, 7-day buffer, chatbot grounded + kill switch |
| Volunteer editorial pipeline unsustainable | High | 6–10 volunteers, defined rotation, degradation policy, buffer absorbs gaps |
| Content doesn't resonate | High | Phase 0 validates before building; kill criteria defined |
| Chabad.org perceives as competitive | Medium | Early complementary-positioning conversation; no audio in Phase 1 |
| Scope creep delays delivery | Medium | Phase 1 scope locked; deferrals documented |

---

## 14. Dependencies & Stakeholder Actions

| # | Action | Owner | When |
|---|--------|-------|------|
| 1 | Confirm standalone vs. ChabadAI backend | Rayi / Merkos | Before build |
| 2 | Seed 3–5 WhatsApp groups + 2–3 teachers for Phase 0 | Rayi | Day 1 |
| 3 | Recruit 6–10 editorial volunteers with rotation | Rayi | Before Phase 1 launch |
| 4 | Initiate Chabad.org partnership conversation | Merkos leadership | First two weeks |
| 5 | Confirm rabbi bandwidth (Zajac, Wolberg, Resnick) | Rayi | Before Phase 1 |
| 6 | Validate Rambam text source with halacha indexing | Rayi | Before build |
| 7 | Begin digitization of reference books | Rayi | At convenience |

---

## 15. Open UX Questions (For Figma Resolution)

1. Artifact display model — passive auto-advance vs. Instagram reel vs. hybrid?
2. Main Zone idle state — ambient visual, teacher photo, episode thumbnail, or black?
3. PiP behavior — automatic or user-pinned?
4. Text Panel position — right sidebar, bottom panel, or floating overlay?
5. Artifact Tray — horizontal strip, vertical sidebar, or hidden by default?
6. Interactive chart handling — pause auto-advance? Audio continues?
7. Source text overlay vs. Text Panel — both always shown? One redundant on mobile?
8. RTL/LTR coexistence — Hebrew content RTL, UI chrome English LTR?
9. Artifact priority within a halacha — priority 1 → Main Zone, where do 2 and 3 go?
10. Playback pause on chatbot open — auto or user-configurable?
11. Text Panel language — Hebrew only or Hebrew + English side by side?

---

*This document consolidates the PRD v3, TRD v1, Master Implementation Plan, Phase 2/3 Spec, and Frontend Mockup Spec into a single authoritative reference.*
