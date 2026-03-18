# Frontend Product Spec

## Merkos Rambam Learning Platform

| | |
|---|---|
| **Owner** | Rayi Stern |
| **Department** | Merkos 302 / ChabadAI |
| **Status** | Pre-Development |
| **Date** | March 2026 |
| **Version** | 2.0 |
| **Related Docs** | BRD (merkos_rambam_brd_intake), TRD (merkos_rambam_trd_v1) |

---

## 1. Product Vision

A mobile-first PWA that delivers daily Rambam learning as a multimodal, media-first experience. The design metaphor is Spotify — not a text reader with images bolted on, but a rich player where visual and audio content are primary, and text is layered in contextually.

**Core premise**: People have short attention spans. The focal point should be media — images, charts, interactive artifacts, video — not walls of text. The Rambam text is present but surfaced the way Spotify handles lyrics: synced, overlayed, optional — not the main event.

**"Multimodal" not "immersive"**: We mean cards, interactive elements, varied media types flowing in and out. We do not mean VR/AR/metaverse.

**Edutainment awareness**: The multimodal experience must serve comprehension, not just engagement. The "raise hand" voice conversation feature is where real retention happens (Socratic back-and-forth). Visuals aid understanding; they don't replace learning.

**Two ends of the spectrum**: The MVP delivery channel is WhatsApp (images, no interface). The full vision is the multimodal player described here. The platform layers from simple to rich over time, without throwing anything away.

---

## 2. Content Types

These are the asset types that flow through the content pipeline and appear in the player experience. Each is generated daily per perek (or per halacha where applicable), reviewed by the editorial team in Notion, and published to the platform.

### 2.1 Conceptual Images

AI-generated educational illustrations that visualize a halacha's core concept.

- **Purpose**: Make abstract or unfamiliar concepts immediately visual.
- **Style**: Clean, dignified, muted palette. No faces or human figures (Jewish artistic tradition). Architectural and object-focused. Historically accurate for Temple-era items. No cartoons, no photorealism.
- **Where it appears**: The hero/album art area on the player screen — this is the primary content stage. Also used as preview thumbnails, share cards, and WhatsApp delivery.
- **Quantity**: 1–3 per perek, tied to the most visually representable halachos.
- **Examples**: See `assets/images/` — the Mishkan in the wilderness, Solomon's First Temple cutaway, Herod's Second Temple aerial view.

### 2.2 Infographics

Structured visual explainers for halachos that involve processes, categories, comparisons, or hierarchies.

- **Purpose**: Break down complex halachic logic into scannable visual form.
- **Where it appears**: In the hero/album art area (synced to audio), and in the scrollable content below the fold.
- **Quantity**: 0–2 per perek, only where the halacha has structural complexity.
- **Examples**: A layout diagram of the Beis HaMikdash sections (Ulam, Heichal, Kodesh HaKodashim). A visual breakdown of the 7 vessels.

### 2.3 Interactive Charts

Explorable, manipulable visual elements (NotebookLM-style).

- **Purpose**: Let the user engage actively — tap, expand, explore.
- **Where it appears**: In the hero/album art area. Should be visually attractive — e.g., the timeline of the Temples should show actual images that cycle when you tap different eras.
- **Quantity**: 0–1 per perek.
- **Examples**: Timeline of the Temples (Mishkan → First Temple → Second Temple) with images cycling per era. A decision-tree for halachic categories.

### 2.4 Sichos Highlights

Cards linking specific halachos to the Rebbe's sichos that reference them.

- **Purpose**: Surface the Rebbe's Torah on the Rambam at the exact point of relevance.
- **Data source**: Existing database of footnotes from the Rebbe's sichos mapped to Rambam. Rayi has a live website with this mapping; a more comprehensive database exists.
- **Where it appears**: In the scrollable content below the fold, appearing at the halacha they reference. Each card includes a pulsing green dot indicator, excerpt, source reference, and a link to the full sicha on chabad.org.
- **Interaction**: Tappable — opens chabad.org link. May also have a playable audio clip.
- **Content example**: Likkutei Sichos Vol. 29 p. 71 (Parshas Re'eh) — explains why the Mishkan was flat but the Mikdash had ascending steps: the Mishkan's sanctity came from its components (temporary), while the Mikdash's sanctity is in the place itself (permanent). Therefore physical elevation expressed spiritual gradation. But no steps between Heichal and Kodesh HaKodashim — because that holiness is beyond measure.
- **Quantity**: Variable per perek.

### 2.5 Perek Overview / Summary

A generated summary card for the perek as a whole.

- **Where it appears**: At the top of the scrollable content below the fold.
- **Quantity**: 1 per perek.

### 2.6 Audio Shiur

The primary audio track — a recorded class on the day's Rambam.

- **Sources**: Multiple rabbis teaching 3 chapters daily — Josh Gordon, Rabbi Zajac, Rabbi Wolberg, Mendel Yusewitz, Raleigh Resnick. Also Rabbi Zions for broader shiurim.
- **Where it appears**: Drives the entire player experience. Fixed mini-bar at bottom. All synced content (text overlay, artifact transitions) is timestamped against this audio.

### 2.7 Video Shiur

A video recording of someone teaching the Rambam.

- **Where it appears**: Picture-in-picture (small floating window) coexisting with the visual artifacts in the hero area.
- **Not every perek will have a video.**

### 2.8 "Did You Know" / Quick Facts

Short, punchy facts related to the day's learning.

- **Where it appears**: In the scrollable content below the fold, and as WhatsApp delivery content.
- **Quantity**: 0–2 per perek.

---

## 3. Player View — Detailed Behavior

### 3.1 Hero / Album Art Area — THE CONTENT STAGE

This is the large area at the top of the player screen. **This is where the content lives** — not below it. It is the equivalent of Spotify's album art, but instead of a static image, it's a live content stage.

- Fills ~70vh of the viewport.
- Displays the current synced artifact: conceptual image, infographic, interactive chart, or vessel diagram.
- **Synced transitions**: As the audio shiur progresses through halachos, the artifact in this area changes. Smooth crossfade transitions.
- **Indicator dots** at the bottom of the hero show which artifact is active and allow manual navigation.
- **Rambam text overlay**: Hebrew text overlayed directly on the content stage, like subtitles on video. Karaoke-style auto-scroll synced to audio — current line is bright, previous fades, upcoming is dimmed. **Toggleable on/off** via a button in the top-right corner.
- **PiP video**: When a video shiur exists, small floating window in the top-left corner of the hero area.
- If no specific artifact is tagged to the current moment, display the perek's primary conceptual image as default.

### 3.2 Scrollable Content Below the Fold

Like Spotify's player screen, scrolling down below the hero reveals supplementary content.

- **Bilingual text blocks**: English on the LEFT, Hebrew on the RIGHT in a two-column grid per halacha. Clean divider between them.
- **Sichos highlight cards**: Appear at the halacha they reference. Pulsing green dot, excerpt, source, link to chabad.org.
- **"Did You Know" cards**: Appear inline in the feed.
- **Share prompt**: At the bottom — "Share today's learning with your community."

### 3.3 Audio Controls

Fixed mini-bar at the bottom of the screen (like Spotify's player bar).

- Play/pause
- Skip forward/back
- Progress scrubber with timestamp
- Playback speed (1x / 1.5x / 2x)

### 3.4 ✋ Raise Hand — PROMINENT

**The hand button is the same size as the play button**, sitting right next to it in the transport controls. It does a periodic wave animation to draw attention.

- **Tap**: Shiur pauses. Full-screen voice conversation UI appears.
- **Interaction model**: Voice — talk back and forth with the AI. Not a text chatbot.
- **AI is grounded in today's learning**: "What was that?" / "What do other mefarshim say?" / "Can you explain that simpler?"
- **Pedagogical grounding**: The conversation should drive actual learning (Socratic, with learning objectives).
- **Return to Shiur**: Button to close and resume audio.

### 3.5 Share

Generate branded, watermarked shareable cards for WhatsApp and social media.

- Available per-artifact and per-perek.
- Cards are self-contained for non-learners encountering them on social.

---

## 4. Other Screens

### 4.1 Home / Content Discovery

Spotify-style home feed.

- **"Today's Learning"**: Hero card with today's perek, featured image, play button.
- **"Other Classes"**: Horizontal scroll row of rabbi cards. All teach 3 chapters daily. Currently: Josh Gordon, Rabbi Zajac, Rabbi Wolberg, Mendel Yusewitz, Raleigh Resnick. **Cards must all be the same size.** Rabbi images in `assets/rabbis/`.
- **"Explore"**: Browse grid by topic area (e.g., The Sanctuary, The Courtyard, Temple Service, Sacrifices).
- **NOTE**: The "Other Classes" section is NOT organized by concept/topic. We learn whatever the Torah teaches us — it's not self-improvement or consumption-based browsing. The rows are organized by *who is teaching*, not *what topic*.

### 4.2 Search

Dedicated search tab.

### 4.3 Raise Hand / Voice Conversation (Full Screen)

- Player dims and pauses
- Voice conversation UI with pulsing ring and waveform bars
- "Ask about Hilchos Beis HaBechirah" / "שאל על הלכות בית הבחירה"
- "Return to Shiur" to resume

### 4.4 Bottom Tab Bar

Home, Search, Saved, Profile.

---

## 5. Design System

### 5.1 Visual Direction

- **Mood**: Dark, moody, Spotify-level polish. Not a "religious app" — a premium media experience.
- **Reference**: Spotify's iOS/Android app for interaction patterns.

### 5.2 Colors

Spotify's palette for the initial build:

- Background: #121212 (base), #181818 / #282828 (surfaces)
- Accent: #1DB954 (Spotify green — will be replaced with brand color in production)
- Text: White primary, #B3B3B3 secondary, #535353 tertiary
- Overlay: Semi-transparent blacks

Final brand palette TBD.

### 5.3 Typography

Modern, clean fonts. **No antiquated "Torah scroll" aesthetic — that's cultural appropriation, not design.**

- UI text: Plus Jakarta Sans, DM Sans, or similar modern sans-serif
- Hebrew text: Noto Sans Hebrew — clean, readable, modern
- The platform should feel contemporary

### 5.4 Component Style

- Rounded corners (12–20px)
- Depth through shadow and opacity, not hard outlines
- Glass-morphism on overlays (backdrop-filter blur)
- Smooth transitions between content
- Spotify-level polish throughout

---

## 6. Content Sync Model

### 6.1 How Sync Works

- Each audio shiur is segmented by halacha (timestamp markers).
- Each content asset is tagged to a specific halacha or range.
- As the audio plays, the player transitions the hero area to the matching artifact, scrolls the karaoke text, etc.
- If no specific artifact is tagged, hero holds the previous artifact or falls back to the perek's default image.

### 6.2 Content Without Audio

The scrollable content below the fold works standalone — a user can scroll through without playing the shiur. The sync layer is additive.

---

## 7. WhatsApp Delivery (MVP Channel)

- Daily broadcast: Featured image(s) + short text summary + link to web
- Images are branded and watermarked (same assets as the player)
- Funnel to the full platform

---

## 8. Rambam Text Reference

The actual Rambam text for Hilchos Beis HaBechirah Perek 1 is in `reference/rambam-beis-habechirah-ch1.md`. This is the source content that the mockup uses. All 14 halachos with English translation and Hebrew with nikud.

---

## 9. Assets Inventory

```
assets/
├── images/
│   ├── mishkan.png          # AI-generated Mishkan in wilderness
│   ├── first-temple.png     # AI-generated Solomon's First Temple
│   └── second-temple.png    # AI-generated Herod's Second Temple
└── rabbis/
    ├── josh-gordon.png      # Josh Gordon headshot
    └── rabbi-zajac.png      # Rabbi Zajac headshot
    # TODO: rabbi-wolberg.png, mendel-yusewitz.png, raleigh-resnick.png
```

---

## 10. Open Questions

- Interactive chart technology and complexity ceiling for Phase 1
- Video PiP behavior when scrolling the content feed
- Voice conversation AI personality and pedagogical guardrails
- Hebrew/English toggle or bilingual default
- RTL layout behavior when mixed with English UI elements
- Brand identity (logo, final color palette, name treatment)
- Exact content discovery mechanisms on the home screen
- How bookmarked moments are stored and resurfaced
- Streak/gamification depth
