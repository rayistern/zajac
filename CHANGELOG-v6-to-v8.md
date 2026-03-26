# Merkos Rambam Mockup: v6 to v8 Changelog

## Overview

Iterative refinement of the Merkos Rambam Learning Platform HTML mockup — a Spotify-inspired dark-theme mobile-first player for daily Rambam Torah learning. All work was done in single-file HTML mockups with inline CSS and JS.

## Session Summary

### 1. Artifact Interactivity Fix (v6)

**Problem:** Inactive hero slides were missing `pointer-events: none`, causing invisible slides to capture all clicks. Dots, timeline pills, and all hero interactions were blocked.

**Fix:** Added `pointer-events: none` to `.hero__slide` and `pointer-events: auto` to `.hero__slide.active`, matching the pattern from the original v4 mockup.

### 2. Raise Hand Button Fix (v6)

**Problem:** The `.tappable:active` CSS rule (`transform: scale(0.97)`) overrode the `translateY(-50%)` on the absolutely-positioned raise hand button, causing it to jump on click.

**Fix:** Added `.player__raise-hand.tappable:active { transform: translateY(-50%) scale(0.95); }` and made transport padding symmetric (`0 72px`) for proper centering.

### 3. Swipe Gesture Support (v6)

Added touch swipe left/right on the hero area to cycle between artifacts (50px threshold).

### 4. Structural Expansion (v6 -> v8)

- **Artifact 2 replaced:** Basic SVG box diagram swapped with a detailed temple structure diagram featuring ambient glows, gradient fills, vessel icons (Menorah, Shulchan, Incense Altar, Aron), dimensional labels, and a Paroches curtain divider.
- **Artifact 4 added:** "Seven Vessels of the Mikdash" — grid layout of all 7 vessels from Halacha 6, with SVG icons, color-coded by location.
- **Artifact 5 added:** "Sanctuary Journey" — vertical timeline from Gilgal through Shiloh, Nov, Givon to Jerusalem, visualizing Halacha 2.
- **Dots updated** from 3 to 5 to match all slides.
- **CSS added** for `.hero__slide--vessels` and `.hero__slide--journey`.

### 5. Self-Contained File (v8)

- All three temple images (mishkan, first-temple, second-temple) embedded as base64 data URIs.
- PiP image (Chabad.org) fetched and embedded as base64.
- File opens correctly from filesystem with no external image dependencies (Google Fonts still loaded via CDN with system font fallback).

### 6. Slide Reordering (v8)

Swapped slides 0 and 1: the interactive timeline is now the first slide (artifact 0), and the temple diagram is second (artifact 1). Updated `goToArtifact()` call in the timeline pill handler from `goToArtifact(1)` to `goToArtifact(0)`.

### 7. Share CTA Removed (v8)

Removed the "Share Branded Card" button and supporting text from the bottom of the page, along with all related CSS.

### 8. Swipe Transition Effect (v8)

Replaced opacity crossfade with horizontal slide transitions:
- CSS: `transform: translateX()` with cubic-bezier easing instead of `opacity`.
- Added `.exit-left` and `.no-transition` utility classes.
- JS: `goToArtifact()` now accepts a `direction` parameter (`'left'` / `'right'`), auto-detected from index comparison.
- Swipe gestures and auto-advance pass correct direction.

## Files

| File | Description |
|------|-------------|
| `mockups/mockup-v6-player.html` | Original v6 with interactivity/raise-hand fixes |
| `mockups/mockup-v7-final.html` | Intermediate version (user-edited) |
| `mockups/mockup-v7-fixed.html` | Intermediate version (user-edited) |
| `mockups/mockup-v8.html` | **Current** — fully self-contained, 5 artifacts, swipe transitions |
