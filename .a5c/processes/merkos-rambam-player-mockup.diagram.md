# Merkos Rambam Player Mockup — Process Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    PHASE 1: DESIGN BRIEF                │
│  Read spec, analyze existing mockup, catalog assets     │
│  Output: design-brief.md with tokens, content, issues   │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              PHASE 2: HERO CONTENT STAGE                │
│  Build 70vh hero area with:                             │
│  • Real PNG images (Mishkan, 1st Temple, 2nd Temple)    │
│  • Artifact cycling with crossfade transitions          │
│  • Karaoke Hebrew text overlay (RTL, auto-scroll)       │
│  • PiP video placeholder + text toggle button           │
│  • Interactive timeline with era selector pills         │
│  • Indicator dots for manual artifact navigation        │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
                   ┌───────────────┐
                   │  BREAKPOINT   │
                   │ Review hero   │
                   │ stage output  │
                   └───────┬───────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│            PHASE 3: PLAYER CONTROLS                     │
│  • Progress scrubber with thumb                         │
│  • Transport: speed, skip, PLAY (56px), skip, 15s      │
│  • ✋ RAISE HAND (56px, same as play, wave animation)   │
│  • Action row: Save, Share                              │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│           PHASE 4: BELOW-FOLD CONTENT                   │
│  • Halachos 1-6 with bilingual layout (EN|HE)          │
│  • Sichos card after Halacha 1 (pulsing dot, link)     │
│  • "Did You Know?" card after Halacha 3                 │
│  • Share CTA at bottom                                  │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│        PHASE 5: VOICE OVERLAY & INTERACTIONS            │
│  • Full-screen voice conversation UI                    │
│  • Pulsing ring + waveform bars                         │
│  • Wire all click handlers                              │
│  • Bottom nav bar (4 tabs)                              │
│  • Touch feedback on all interactive elements           │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│          PHASE 6: POLISH & VERIFICATION                 │
│  • Glass-morphism, shadows, transitions                 │
│  • Animation timing and staggering                      │
│  • Spec compliance checklist                            │
│  • Responsive behavior (375px → 768px)                  │
│  • Final quality gate                                   │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
                   ┌───────────────┐
                   │  BREAKPOINT   │
                   │ Final review  │
                   │ of complete   │
                   │ mockup        │
                   └───────┬───────┘
                           │
                           ▼
                      ✅ COMPLETE
```
