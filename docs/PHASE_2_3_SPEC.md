# Phase 2 & 3 Spec
## Immersive Player Frontend + Voice Chatbot

---

## Table of Contents

1. [Vision](#vision)
2. [Phase 2 — Immersive Player](#phase-2)
   - [Layout Zones](#layout-zones)
   - [Media Layer](#media-layer)
   - [Artifact Display Model](#artifact-display-model)
   - [Source Text Overlay](#source-text-overlay)
   - [Text Panel](#text-panel)
   - [Secondary Texts (deferred within Phase 2)](#secondary-texts)
   - [Desktop vs. Mobile](#desktop-vs-mobile)
   - [Data Requirements](#data-requirements)
   - [Schema Additions](#schema-additions)
   - [Open UX Questions for Figma](#open-ux-questions)
3. [Phase 3 — Voice Chatbot](#phase-3)
   - [Interaction Model](#interaction-model)
   - [Context Package](#context-package)
   - [Data Requirements](#chatbot-data)
   - [Schema Additions](#chatbot-schema)
4. [API Endpoints Needed](#api-endpoints)
5. [Open Questions](#open-questions)

---

## 1. Vision <a name="vision"></a>

The goal is not a podcast player. It is not a video player. It is not a text study interface. It is all three, unified into something that feels like none of them individually — an **immersive content experience** where audio/video, generated artifacts, and source text move together in sync with the class.

Reference points:
- Video podcast platforms (Spotify video, YouTube) — but with layered content
- Torah study platforms — but not static, not text-first
- Interactive documentary — artifacts appear and recede as the content demands them
- The teacher is present (voice, or video if available) but the screen is alive with what they're teaching

The experience should feel like sitting in the shiur with a brilliant visual assistant who's reading along and surfacing exactly the right thing at exactly the right moment.

---

## 2. Phase 2 — Immersive Player <a name="phase-2"></a>

### 2.1 Layout Zones <a name="layout-zones"></a>

The screen is divided into named zones. The exact sizing, proportions, and transitions are for Figma. The zones:

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│                  MAIN ZONE                          │
│   (video / artifact / dynamic content section)      │
│                                                     │
│   [source text overlay — subtitle style]            │
│                                                     │
├───────────────────────┬─────────────────────────────┤
│                       │                             │
│   ARTIFACT TRAY       │   TEXT PANEL                │
│   (queue of upcoming  │   (primary source text,     │
│   or active artifacts │   active halacha            │
│   — image, chart,     │   highlighted)              │
│   infographic, etc.)  │                             │
│                       │                             │
├───────────────────────┴─────────────────────────────┤
│              PLAYBACK CONTROLS                      │
│   ◀◀  ▶  ▶▶   ────●──────────────   🖐 (chatbot)  │
└─────────────────────────────────────────────────────┘
```

**MAIN ZONE** — the dominant visual surface. Contains one of:
- The original talking-head video (if episode has `video_url`)
- The current active image artifact (if no video, or if an image artifact is scheduled at this timestamp)
- A dynamic content section (interactive chart, infographic) if that artifact type is active
- A neutral holding state (ambient visual) when nothing is scheduled

**ARTIFACT TRAY** — horizontal strip or panel showing artifacts that are active or coming up. Could show thumbnails of images, icons for chart types, etc. User can interact to bring one into the Main Zone.

**TEXT PANEL** — the source text (Rambam Hebrew, or whatever `work` is being studied). Scrolls to keep the active source unit in view as playback progresses. Active halacha is highlighted. Could expand to show multiple halachot for context.

**SOURCE TEXT OVERLAY** — Rambam text displayed directly on the Main Zone, subtitle-style, synced to the transcript alignment. Shows the Hebrew text of the active source unit. Not the transcript — the original source text.

**PLAYBACK CONTROLS** — standard. The 🖐 (hand emoji) is the Phase 3 chatbot entry point.

---

### 2.2 Media Layer <a name="media-layer"></a>

The player supports three media source scenarios:

**Scenario A — Audio only (no video)**
- Main Zone shows artifacts on their schedule
- When no artifact is active: ambient visual (class thumbnail, or a neutral branded background)
- This is the default for most current episodes

**Scenario B — Video available (talking head)**
- Main Zone defaults to the video
- When an image artifact is scheduled: video moves to Picture-in-Picture (PiP), artifact takes Main Zone
- When artifact ends: video returns to Main Zone
- User can manually pin video to Main Zone (artifact displays in Tray instead)
- Interactive artifacts (charts, infographics) may appear in a lower section without displacing video — TBD in Figma

**Scenario C — No source media (future)**
- Episode is text-only, no audio/video
- Main Zone is entirely artifact-driven

The `episodes` table already has `video_url` and `s3_video_key` (added in master plan). Player logic: if `video_url` is populated → Scenario B, else → Scenario A.

---

### 2.3 Artifact Display Model <a name="artifact-display-model"></a>

**Timing** is derived from the `artifact_timeline` DB view (see master plan §3.9). Each artifact has a `display_start_ms` and `display_end_ms` computed from the alignment window and the artifact's `position` float.

**Display semantics** — this is the key UX question for Figma. Options being considered:

*Option A — Instagram Reel model:*
Artifacts display sequentially within a halacha's window, each one filling the Main Zone (or a section) until the user swipes/taps to advance or a timeout expires. Audio continues regardless of where the user is in the artifact sequence. At the end of the halacha, next halacha's artifacts begin.

*Option B — Passive slideshow:*
Artifacts auto-advance on schedule (per computed display window). No user interaction required. Audio and visual stay in sync automatically.

*Option C — Hybrid:*
Default is passive auto-advance (Option B). User can tap to pause an artifact (freeze it in place while audio continues), or tap to dismiss and see the next one early.

**Recommendation for Figma exploration:** Start with Option C. The "pause artifact while audio continues" mechanic is natural — like pausing a slide while listening to the speaker.

**Artifact types and their display behavior:**

| Type | Main Zone behavior | Notes |
|---|---|---|
| `image / illustration` | Full Main Zone | Displaces video to PiP |
| `image / diagram` | Full Main Zone or lower section | May not need to displace video |
| `image / infographic` | Full Main Zone | User might want to explore it |
| `image / chart` | Lower section or full | Depends on complexity |
| `image / timeline` | Full Main Zone | Horizontal layout |
| `interactive` (future) | Full Main Zone | User interaction suspends auto-advance |
| `video` (future) | Full Main Zone | Replaces teacher video temporarily |
| `text` (future) | Text Panel or overlay | Doesn't displace Main Zone |

---

### 2.4 Source Text Overlay <a name="source-text-overlay"></a>

The original Hebrew source text (Rambam, or whatever work) overlaid on the Main Zone, subtitle-style. Synced to playback via the `alignments` table — when `alignment.start_ms` is reached, the corresponding `source_units.hebrew_text` appears.

Display rules:
- Show the active source unit's Hebrew text
- Fade in at `halacha_start_ms`, fade out at `halacha_end_ms`
- Right-aligned, RTL, Hebrew font
- User can toggle off
- Configurable font size

This is **not** the transcript. It is the original canonical text, surfaced at the moment the teacher is discussing it.

---

### 2.5 Text Panel <a name="text-panel"></a>

A dedicated panel showing the source text in readable form. The active halacha is highlighted and scrolled into view as playback progresses. The panel shows surrounding halachot for context (configurable: show N halachot before/after active).

User can click any halacha in the panel to jump playback to the point where that halacha begins (if covered in this episode).

The Text Panel can be collapsed on mobile, expanded on desktop.

---

### 2.6 Secondary Texts — deferred within Phase 2 <a name="secondary-texts"></a>

Commentaries, Talmudic sources, Rishonim, etc. are explicitly deferred to a later sub-phase of Phase 2. The schema will need a `source_unit_links` table to model cross-work references. Design question: does the Text Panel show one work at a time (togglable), or multiple simultaneously? To be resolved in Figma.

**Schema addition needed (Phase 2, not now):**
```sql
CREATE TABLE source_unit_links (
    id SERIAL PRIMARY KEY,
    source_unit_id INTEGER NOT NULL REFERENCES source_units(id),
    linked_unit_id INTEGER NOT NULL REFERENCES source_units(id),
    link_type TEXT,       -- 'commentary' | 'source' | 'parallel' | 'contradiction'
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 2.7 Desktop vs. Mobile <a name="desktop-vs-mobile"></a>

**Desktop:**
- All zones visible simultaneously
- Text Panel expanded by default (right sidebar or bottom panel)
- Artifact Tray visible
- Wider Main Zone
- Chatbot (Phase 3) available as sidebar or floating panel

**Mobile:**
- Main Zone full width, dominant
- Text Panel collapsed by default — tap to expand as bottom sheet
- Artifact Tray as horizontal scroll strip below Main Zone
- Source text overlay on Main Zone
- Chatbot as floating button (🖐)

The player is designed mobile-first for consumption, desktop-first for study.

---

### 2.8 Data Requirements <a name="data-requirements"></a>

The frontend needs from the backend:

**On episode load:**
```
GET /api/episode/:id/timeline

Returns:
{
  episode: { id, title, audio_url, video_url, duration_ms },
  halachot: [
    {
      source_unit_id,
      sefaria_ref,
      hebrew_text,
      start_ms,
      end_ms,
      artifacts: [
        {
          artifact_version_id,
          artifact_type,
          subtype,
          priority,
          position,
          display_start_ms,
          display_end_ms,
          url,
          style_name
        }
      ]
    }
  ]
}
```

**On playback (lightweight, for transcript sync):**
```
GET /api/episode/:id/transcript/at/:ms

Returns the active word and source unit at that timestamp.
(Or: the full transcript is loaded upfront and seeking is done client-side)
```

**Recommendation:** load the full timeline upfront on episode load. No polling during playback. All seeking is client-side using the loaded data.

---

### 2.9 Schema Additions <a name="schema-additions"></a>

The only addition needed now (before Phase 2 begins) is confirming `video_url` and `s3_video_key` are on `episodes` — already added to the master plan.

The `artifact_timeline` view already handles display timing derivation — already in the master plan.

Everything else (secondary texts `source_unit_links`, frontend API routes) is Phase 2 work.

---

### 2.10 Open UX Questions for Figma <a name="open-ux-questions"></a>

These are explicitly unresolved and should be explored in Figma before any frontend code is written:

1. **Artifact display model** — passive auto-advance vs. Instagram reel vs. hybrid?
2. **What happens in the Main Zone when nothing is scheduled?** Ambient visual, teacher photo, episode thumbnail, or black?
3. **PiP behavior** — when an image displaces video, does the PiP appear automatically or does the user pin it?
4. **Text Panel position** — right sidebar, bottom panel, or floating overlay?
5. **Artifact Tray** — horizontal strip, vertical sidebar, or hidden by default?
6. **How to handle an interactive chart** (future type) — does it pause the auto-advance? Does audio continue?
7. **Source text overlay vs. Text Panel** — are both always shown? Is one redundant on mobile?
8. **RTL/LTR layout** — primary language is Hebrew (RTL), UI chrome is English (LTR). How do these coexist?
9. **Artifact priority within a halacha** — priority 1 goes to Main Zone. Where do priorities 2 and 3 go simultaneously?

---

## 3. Phase 3 — Voice Chatbot <a name="phase-3"></a>

### 3.1 Interaction Model <a name="interaction-model"></a>

A single 🖐 (hand emoji) button in the playback controls. User taps it. Playback pauses (or continues — TBD). A voice interface opens. User speaks a question. The system responds with voice.

The framing: the user is **talking to the podcast** — not to a generic AI assistant. The chatbot knows exactly where in the class the user is, what halacha is being discussed, what the teacher just said, and what artifacts have been shown.

**Interaction flow:**
1. User taps 🖐
2. Playback optionally pauses (configurable or user choice)
3. Microphone opens — user speaks
4. Voice → text (STT)
5. Context package assembled (see §3.2)
6. LLM generates response
7. Text → voice (TTS)
8. Response plays back
9. User can ask follow-up or dismiss
10. Playback resumes

---

### 3.2 Context Package <a name="context-package"></a>

What gets sent to the LLM:

```
System prompt:
  You are a study assistant for a Torah class. The user is currently
  listening to a class on [work title] by [teacher name].
  Answer questions based on the content of the class and the source text.
  Be concise. The response will be spoken aloud.

Context:
  Current timestamp: {current_ms}
  Active source unit: {sefaria_ref} — {hebrew_text} (+ translation if available)
  
  Transcript up to this point (last N minutes or last M tokens):
  {merged_transcript truncated at current_ms}
  
  Halachot covered so far in this episode:
  {list of sefaria_refs with brief summaries}
  
  Artifacts shown so far:
  {list of artifact subtypes and their source units}

User question: {transcribed voice input}
```

**Transcript truncation strategy:** include the last 10 minutes of transcript (configurable), not the full episode. Older content is summarized at the halacha level rather than included verbatim. This keeps the context window manageable and costs predictable.

**The cutoff is the current playback timestamp** — the chatbot only knows what has been said up to where the user is in the class. It does not have access to future content in the episode.

---

### 3.3 Data Requirements <a name="chatbot-data"></a>

**At the moment the user taps 🖐, the frontend sends:**
```json
{
  "episode_id": 42,
  "current_ms": 874000,
  "question_audio": "<base64 or blob>"
}
```

**The API endpoint:**
```
POST /api/chatbot/query

1. Transcribe question_audio → text (STT, e.g. Whisper)
2. Fetch context package:
   - episode transcript truncated at current_ms
   - source units covered up to current_ms (from alignments)
   - artifacts displayed up to current_ms (from artifact_timeline view)
3. Call LLM with context + question
4. TTS response
5. Return audio blob + text transcript of response
```

All the data needed (transcripts, alignments, source units, artifacts) is already in the schema. No new tables required.

---

### 3.4 Schema Additions <a name="chatbot-schema"></a>

One optional logging table (useful for quality improvement):

```sql
CREATE TABLE chatbot_sessions (
    id SERIAL PRIMARY KEY,
    episode_id INTEGER NOT NULL REFERENCES episodes(id),
    playback_ms_at_query INTEGER NOT NULL,
    active_source_unit_id INTEGER REFERENCES source_units(id),
    question_text TEXT,
    response_text TEXT,
    llm_model TEXT,
    stt_model TEXT,
    tts_model TEXT,
    context_tokens_used INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

This lets you review chatbot interactions, spot common questions, and improve the context package or LLM prompt over time.

---

## 4. API Endpoints Needed <a name="api-endpoints"></a>

These extend `api.py` (currently only webhooks). Phase 2 adds read endpoints:

```
# Episode timeline (all artifacts + halachot + media)
GET  /api/episode/:id/timeline

# Source unit text at a timestamp
GET  /api/episode/:id/source-unit/at/:ms

# Full transcript (for client-side seeking)
GET  /api/episode/:id/transcript

# Class listing
GET  /api/classes

# Episodes for a class
GET  /api/class/:id/episodes
```

Phase 3 adds:
```
# Voice query
POST /api/chatbot/query
```

Authentication, rate limiting, and CORS are Phase 2 concerns — not specified here.

---

## 5. Open Questions <a name="open-questions"></a>

1. **Playback pause on chatbot open** — should audio pause when user taps 🖐, or continue? Probably user-configurable.

2. **Chatbot voice** — what voice/TTS provider? Should it have a consistent character (e.g. same voice for all sessions)?

3. **Follow-up questions** — does the chatbot maintain conversation history within a session, or is each question independent?

4. **Offline / low-connectivity** — is the player expected to work offline or with poor connectivity? Affects whether timeline is loaded upfront or streamed.

5. **Authentication** — who can access the player? Public, subscribers only, same as WhatsApp subscriber list?

6. **Artifact interaction on mobile** — if a user is on mobile and wants to "explore" an infographic, how does that interact with the auto-advance model?

7. **Text Panel language** — show Hebrew only, or Hebrew + English translation side by side? Sefaria has English translations for most works.
