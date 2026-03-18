# Merkos Rambam Player Mockup — Process Description

## Goal
Create a polished, player-focused single-file HTML mockup for the Merkos Rambam Learning Platform. The mockup should use real AI-generated images, have all interactive elements clickable, and achieve Spotify-level visual polish.

## Scope
- **Player view only** (not Home, Search, etc.)
- Single self-contained HTML file with relative image paths
- All CSS in `<style>`, all JS in `<script>`
- Mobile-first (375px target, responsive to 768px)

## Phases

### Phase 1: Design Brief
Analyze the product spec, catalog all assets, extract all reference text content, and identify issues in the existing mockup to avoid repeating them.

### Phase 2: Hero Content Stage
Build the ~70vh hero area — the core visual experience. Uses real PNG images from `assets/images/`, artifact cycling with smooth crossfades, Hebrew karaoke text overlay, PiP placeholder, and interactive timeline with era selector pills.

### Phase 3: Player Controls
Add the audio transport: progress scrubber, play/pause, skip controls, speed selector, and the prominent Raise Hand button (same 56px size as play, with wave animation).

### Phase 4: Below-Fold Content
Scrollable content below the hero: all 6 halachos with bilingual English/Hebrew layout, Sichos insight card with pulsing indicator, "Did You Know?" card, and share CTA.

### Phase 5: Voice Overlay & Interactions
Full-screen voice conversation UI triggered by the Raise Hand button. Wire all click handlers, add bottom nav, ensure every interactive element works.

### Phase 6: Polish & Verification
Glass-morphism, shadows, animation timing, responsive behavior, and systematic verification against the product spec checklist.

## Quality Gates
- **After Phase 2**: User reviews hero stage for image loading, artifact cycling, and karaoke positioning
- **After Phase 6**: User reviews complete mockup for overall quality and spec compliance

## Output
`merkos-rambam-frontend/mockups/mockup-v6-player.html`
