# Merkos Rambam — Frontend Mockup Package

## What This Is

This is a frontend design package for the Merkos Rambam Learning Platform — a Spotify-inspired mobile-first PWA for daily Rambam (Maimonides) Torah learning. The goal is to build a multimodal player where visual content (AI-generated images, interactive charts, infographics) is the primary experience, and text is secondary/overlayed.

## Project Structure

```
merkos-rambam-frontend/
├── README.md                          # This file
├── specs/
│   └── frontend-product-spec-v2.md    # THE SPEC — full product requirements
├── mockups/
│   ├── mockup-latest.html             # Latest HTML mockup (v5, has embedded images but some layout issues)
│   └── mockup-v4-stable.html          # Stable v4 mockup (works well, fewer images embedded)
├── assets/
│   ├── images/
│   │   ├── mishkan.png                # AI-generated: Mishkan in the wilderness
│   │   ├── first-temple.png           # AI-generated: Solomon's First Temple cutaway
│   │   └── second-temple.png          # AI-generated: Herod's Second Temple aerial
│   └── rabbis/
│       ├── josh-gordon.png            # Josh Gordon headshot
│       └── rabbi-zajac.png            # Rabbi Zajac headshot
└── reference/
    ├── rambam-beis-habechirah-ch1.md  # Actual Rambam text (Halachos 1-6+) with English + Hebrew
    └── sichos-beis-habechirah.md      # Rebbe's sichos reference with link and synopsis
```

## How To Use This

### For Claude Code

Read `specs/frontend-product-spec-v2.md` first — that's the source of truth. Then look at the mockups for visual reference. The mockup-v4-stable is more reliable for layout; mockup-latest has more features but some layout issues that need fixing.

### Key Design Decisions (from product owner)

1. **The "album art" area IS the content stage.** Images, charts, and interactive artifacts display IN the hero area (70vh), synced to audio. Text and supplementary content scroll below the fold.

2. **Spotify's color palette** for now (#121212 base, #1DB954 green accent). Will be replaced with brand colors later.

3. **Modern fonts only.** Plus Jakarta Sans / DM Sans for UI, Noto Sans Hebrew for Hebrew text. No antiquated Torah-scroll aesthetic.

4. **Bilingual layout**: English LEFT, Hebrew RIGHT in side-by-side columns per halacha block.

5. **"Other Classes" not "Continue Learning"**: Organized by rabbi (who is teaching), not by topic. All classes are 3 chapters daily. Rabbis: Josh Gordon, Rabbi Zajac, Rabbi Wolberg, Mendel Yusewitz, Raleigh Resnick. All card thumbnails must be the same size.

6. **✋ Raise Hand button** is prominent — same size as play button, in the transport controls, with a periodic wave animation.

7. **Sichos cards** link to chabad.org (e.g., https://www.chabad.org/torah-texts/7208442). They appear in the below-fold content at the halacha they reference.

8. **Interactive timeline** shows actual images that cycle when clicking different eras (Mishkan, First Temple, Second Temple). Uses the vertical list style from the mockups.

9. **Karaoke text overlay** on the hero area — Hebrew text synced to audio, toggleable on/off.

10. **No "The Rebbe speaks on this" floating indicator.** Sichos are surfaced in the below-fold content only.

### Known Issues in Latest Mockup

- Some layout overlap issues in the timeline artifact
- Rabbi card sizes may be inconsistent
- File is ~2.5MB due to embedded base64 images (use external assets in production)

### Tech Stack (from TRD)

- Next.js 14+ (App Router)
- TypeScript
- Tailwind CSS + Radix UI
- Supabase (PostgreSQL)
- Cloudflare R2 (image storage)
- Vercel (hosting)
