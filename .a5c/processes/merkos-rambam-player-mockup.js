/**
 * @process merkos-rambam-player-mockup
 * @description Build a polished, player-focused HTML mockup for the Merkos Rambam Learning Platform
 * with real images, interactive elements, and Spotify-level polish.
 * @inputs { specPath: string, assetsPath: string, referencePath: string, existingMockupPath: string, outputPath: string }
 * @outputs { success: boolean, mockupPath: string, artifacts: array }
 *
 * @skill tailwind-css specializations/web-development/skills/tailwind-css/SKILL.md
 * @skill react-development specializations/web-development/skills/react-development/SKILL.md
 * @agent frontend-architect specializations/web-development/agents/frontend-architect/AGENT.md
 * @agent component-developer specializations/web-development/agents/component-developer/AGENT.md
 * @agent animation-developer specializations/web-development/agents/animation-developer/AGENT.md
 */

import { defineTask } from '@a5c-ai/babysitter-sdk';

/**
 * Merkos Rambam Player Mockup Process
 *
 * Builds a polished single-file HTML mockup focused on the Player view.
 *
 * Phases:
 * 1. Design Brief - Analyze spec, assets, and existing mockup issues
 * 2. Hero Content Stage - Build the main hero area with real images, artifact cycling, karaoke
 * 3. Player Controls + Transport - Scrubber, play/pause, hand button, speed controls
 * 4. Below-Fold Content - Bilingual text blocks, sichos cards, DYK, share CTA
 * 5. Voice Overlay + Interactions - Full-screen voice UI, all clickable interactions
 * 6. Polish & Verification - Animations, transitions, glass-morphism, responsive, spec compliance
 */
export async function process(inputs, ctx) {
  const {
    specPath = 'merkos-rambam-frontend/specs/frontend-product-spec-v2.md',
    assetsPath = 'merkos-rambam-frontend/assets',
    referencePath = 'merkos-rambam-frontend/reference',
    existingMockupPath = 'merkos-rambam-frontend/mockups/mockup-v4-stable.html',
    outputPath = 'merkos-rambam-frontend/mockups/mockup-v6-player.html'
  } = inputs;

  const startTime = ctx.now();
  const artifacts = [];

  ctx.log('info', 'Starting Merkos Rambam Player Mockup Process');

  // ============================================================================
  // PHASE 1: DESIGN BRIEF & ANALYSIS
  // ============================================================================

  ctx.log('info', 'Phase 1: Analyzing spec, assets, and existing mockup issues');

  const designBrief = await ctx.task(designBriefTask, {
    specPath,
    assetsPath,
    referencePath,
    existingMockupPath,
    outputPath
  });

  // ============================================================================
  // PHASE 2: BUILD HERO CONTENT STAGE
  // ============================================================================

  ctx.log('info', 'Phase 2: Building hero content stage with real images and artifacts');

  const heroStage = await ctx.task(buildHeroStageTask, {
    designBrief,
    assetsPath,
    referencePath,
    outputPath
  });

  // Breakpoint: Review hero stage
  await ctx.breakpoint({
    question: 'The hero content stage has been built. Please open the mockup file and check:\n- Do the real images (Mishkan, First Temple, Second Temple) display properly?\n- Does artifact cycling work when clicking indicator dots?\n- Is the karaoke text overlay positioned correctly?\n- Does the PiP video placeholder look right?\n\nApprove to continue, or reject with feedback.',
    title: 'Hero Stage Review'
  });

  // ============================================================================
  // PHASE 3: PLAYER CONTROLS & TRANSPORT
  // ============================================================================

  ctx.log('info', 'Phase 3: Adding player controls and transport bar');

  const playerControls = await ctx.task(buildPlayerControlsTask, {
    designBrief,
    outputPath
  });

  // ============================================================================
  // PHASE 4: BELOW-FOLD CONTENT
  // ============================================================================

  ctx.log('info', 'Phase 4: Building below-fold content with bilingual text and sichos cards');

  const belowFold = await ctx.task(buildBelowFoldTask, {
    designBrief,
    referencePath,
    outputPath
  });

  // ============================================================================
  // PHASE 5: VOICE OVERLAY & ALL INTERACTIONS
  // ============================================================================

  ctx.log('info', 'Phase 5: Adding voice overlay and all interactive elements');

  const interactions = await ctx.task(buildInteractionsTask, {
    designBrief,
    outputPath
  });

  // ============================================================================
  // PHASE 6: POLISH & SPEC VERIFICATION
  // ============================================================================

  ctx.log('info', 'Phase 6: Final polish - animations, glass-morphism, responsive, spec check');

  const polish = await ctx.task(polishAndVerifyTask, {
    designBrief,
    specPath,
    outputPath
  });

  // Final breakpoint: Review complete mockup
  await ctx.breakpoint({
    question: 'The complete player mockup is ready. Please open it and verify:\n- All images load properly\n- All interactive elements are clickable\n- Animations and transitions are smooth\n- Layout and spacing feel premium/Spotify-level\n- Bilingual text (English left, Hebrew right) is correct\n- Raise Hand button is prominent and animated\n\nApprove to finalize, or reject with specific feedback for refinement.',
    title: 'Final Mockup Review'
  });

  return {
    success: true,
    mockupPath: outputPath,
    artifacts,
    duration: ctx.now() - startTime
  };
}

// ============================================================================
// TASK DEFINITIONS
// ============================================================================

const designBriefTask = defineTask('design-brief', (args, taskCtx) => ({
  kind: 'agent',
  title: 'Analyze spec and create design brief',
  agent: {
    name: 'general-purpose',
    prompt: {
      role: 'Senior UI/UX analyst',
      task: `Read and analyze the following files to create a comprehensive design brief for an HTML mockup:

1. Product spec: ${args.specPath} - Read Section 3 (Player View) thoroughly
2. Existing mockup: ${args.existingMockupPath} - Analyze what works and what needs fixing
3. Available assets: List files in ${args.assetsPath}/images/ and ${args.assetsPath}/rabbis/
4. Reference content: ${args.referencePath}/rambam-beis-habechirah-ch1.md and ${args.referencePath}/sichos-beis-habechirah.md

Create a design brief document at .a5c/runs/design-brief.md that includes:
- Exact color values, fonts, and design tokens from the spec
- List of all available image assets with their file paths
- All Rambam text content (halachos 1-6 with Hebrew and English)
- Sichos reference content for inline cards
- Specific issues found in the existing mockup that must be fixed
- Checklist of spec requirements for the Player view

Focus on Section 3 of the spec (Player View Detailed Behavior) and Section 5 (Design System).
The output file path is: ${args.outputPath}`,
      instructions: [
        'Read each file carefully and extract all relevant details',
        'Note exact hex colors, font names, border-radius values, spacing',
        'List every interactive element the spec requires',
        'Identify what the existing mockup gets wrong',
        'Create the design brief as a markdown file'
      ],
      outputFormat: 'JSON with keys: designTokens, assets, content, issues, requirements'
    }
  },
  io: {
    inputJsonPath: `tasks/${taskCtx.effectId}/input.json`,
    outputJsonPath: `tasks/${taskCtx.effectId}/output.json`
  }
}));

const buildHeroStageTask = defineTask('build-hero-stage', (args, taskCtx) => ({
  kind: 'agent',
  title: 'Build hero content stage with real images',
  agent: {
    name: 'general-purpose',
    prompt: {
      role: 'Expert frontend developer specializing in HTML/CSS mockups',
      task: `Create the initial HTML mockup file at ${args.outputPath} with the hero/content stage.

This is a PLAYER VIEW mockup for the Merkos Rambam Learning Platform — a Spotify-inspired dark-theme mobile-first PWA.

CRITICAL REQUIREMENTS:
- Single self-contained HTML file (except images referenced via relative paths)
- Mobile-first (375px viewport), but should look good up to tablet
- Dark theme: #121212 base, #181818 surfaces, #282828 elevated, #1DB954 green accent
- Fonts: Plus Jakarta Sans for UI, DM Sans for body, Noto Sans Hebrew for Hebrew text (load from Google Fonts)
- Images: Use relative paths like ../assets/images/mishkan.png, ../assets/images/first-temple.png, ../assets/images/second-temple.png

BUILD THE HERO CONTENT STAGE:
1. Top bar: Back chevron (left), "NOW PLAYING" label + "Hilchos Beis HaBechirah" title (center), share icon (right). Sticky, glass-morphism background.
2. Hero area (~70vh): The main content stage. Contains:
   a. Three artifacts (cycling): Mishkan image, First Temple image, Second Temple image — using the REAL PNG files from ../assets/images/
   b. Each image should fill the hero area nicely with object-fit: cover
   c. Smooth crossfade transitions between artifacts (0.8s opacity)
   d. Indicator dots at bottom of hero (3 dots, active one is green pill shape)
   e. Karaoke text overlay at bottom of hero — Hebrew text in Noto Sans Hebrew, right-to-left, with past/current/next line styling
   f. Text toggle button (top-right) to show/hide karaoke
   g. PiP video placeholder (top-left, small rounded rectangle)
   h. Gradient fade at very bottom of hero blending into the dark background
3. Interactive timeline artifact (third artifact): Era selector pills for Mishkan/1st Temple/2nd Temple with color-coded borders, cycling the displayed image

Make the indicator dots clickable to switch artifacts. Include auto-cycling every 5 seconds. Include the karaoke animation that cycles through Hebrew text lines.

Use the EXACT Rambam Hebrew text from the reference:
- Past: שֶׁנֶּאֱמַר וְעָשׂוּ לִי מִקְדָּשׁ
- Current: מִצְוַת עֲשֵׂה לַעֲשׂוֹת בַּיִת לַה׳
- Next: מוּכָן לִהְיוֹת מַקְרִיבִין בּוֹ הַקָּרְבָּנוֹת

Write the COMPLETE HTML file with all CSS in a <style> tag and all JS in a <script> tag. Use CSS custom properties for the design tokens. Include placeholder sections (empty divs with comments) for player controls and below-fold content that will be filled in later phases.`,
      instructions: [
        'Write the complete HTML file — not a fragment, the full document',
        'Use real image paths: ../assets/images/mishkan.png, ../assets/images/first-temple.png, ../assets/images/second-temple.png',
        'All CSS must use custom properties defined in :root',
        'All interactive elements must have cursor: pointer and appropriate hover/active states',
        'Include smooth transitions and animations',
        'The file must work when opened directly from the mockups/ folder in a browser',
        'Write the output to: ' + args.outputPath
      ],
      outputFormat: 'JSON with keys: success, filePath, elementsCreated'
    }
  },
  io: {
    inputJsonPath: `tasks/${taskCtx.effectId}/input.json`,
    outputJsonPath: `tasks/${taskCtx.effectId}/output.json`
  }
}));

const buildPlayerControlsTask = defineTask('build-player-controls', (args, taskCtx) => ({
  kind: 'agent',
  title: 'Add player controls and transport bar',
  agent: {
    name: 'general-purpose',
    prompt: {
      role: 'Expert frontend developer',
      task: `Edit the existing mockup file at ${args.outputPath} to add player controls below the hero stage.

ADD THESE ELEMENTS (in order, below the hero):

1. PROGRESS SCRUBBER:
   - Full-width thin bar (3px height, #282828 track, white fill)
   - White circle thumb on the fill edge
   - Time labels below: "4:20" left, "12:45" right
   - Font size 10px, color #535353

2. TRANSPORT CONTROLS (centered row):
   - Speed button "1x" (small pill, border, grey text) — LEFT side
   - Skip back button (double chevron left SVG)
   - PLAY BUTTON (56px circle, white background, dark play icon) — CENTER
   - Skip forward button (double chevron right SVG)
   - "15s" label (small pill) — RIGHT side
   - ✋ RAISE HAND BUTTON (56px circle, same size as play button!) — sits right next to play button
     * Green-tinted background (rgba(29,185,84,0.15))
     * Green border (rgba(29,185,84,0.3))
     * Wave emoji with periodic wave animation (rotate keyframes, 2.5s, with 3s delay)
     * This is PROMINENT — same visual weight as play button

3. ACTION ROW (below transport):
   - Save button (bookmark SVG + text)
   - Share button (share SVG + text)
   - Both grey, subtle

IMPORTANT from the spec:
- "The hand button is the same size as the play button, sitting right next to it in the transport controls"
- "It does a periodic wave animation to draw attention"

Use SVG icons (inline). All buttons must have cursor:pointer, hover states, and touch feedback (scale on active).`,
      instructions: [
        'Read the existing file first, then edit it',
        'Add the controls section between the hero stage and the below-fold placeholder',
        'Ensure the raise hand button is truly the same size (56px) as the play button',
        'Include the wave animation keyframes',
        'All SVG icons should be clean and minimal'
      ],
      outputFormat: 'JSON with keys: success, elementsAdded'
    }
  },
  io: {
    inputJsonPath: `tasks/${taskCtx.effectId}/input.json`,
    outputJsonPath: `tasks/${taskCtx.effectId}/output.json`
  }
}));

const buildBelowFoldTask = defineTask('build-below-fold', (args, taskCtx) => ({
  kind: 'agent',
  title: 'Build below-fold content with bilingual text and sichos',
  agent: {
    name: 'general-purpose',
    prompt: {
      role: 'Expert frontend developer with bilingual layout experience',
      task: `Edit the existing mockup at ${args.outputPath} to add the below-fold scrollable content section.

Read the reference content from:
- ${args.referencePath}/rambam-beis-habechirah-ch1.md (Halachos 1-6, English + Hebrew)
- ${args.referencePath}/sichos-beis-habechirah.md (Sichos card content)

ADD THESE ELEMENTS in the below-fold section:

1. SECTION DIVIDER: Thin horizontal line (1px, rgba(255,255,255,0.06))

2. FOR EACH HALACHA (1 through 6):
   a. Section label: "HALACHA N" — 10px uppercase, letter-spacing 2px, #535353
   b. Halacha block (rounded card, #181818 background, 20px border-radius):
      - Large green number (28px, bold, #1DB954)
      - BILINGUAL LAYOUT: Two columns side by side
        * LEFT column: English text (13px, line-height 1.7, white at 85% opacity)
        * RIGHT column: Hebrew text (14px, Noto Sans Hebrew, RTL, line-height 1.9, white at 60% opacity)
        * Divider between columns: 1px left border on Hebrew column
      - Use the ACTUAL Rambam text from the reference files

3. SICHOS CARD (appears after Halacha 1, where it's referenced):
   - Gradient background (#181818 to #282828, 135deg)
   - Green glow effect (radial gradient, top-right)
   - Badge: pulsing green dot + "THE REBBE'S INSIGHT" label
   - Excerpt text (italic, grey, 14px)
   - Hebrew source text: לקוטי שיחות חכ״ט ע׳ 71
   - Source reference: "Likkutei Sichos Vol. 29 p. 71 · Parshas Re'eh"
   - Small play button (audio clip indicator)
   - Clickable — links to https://www.chabad.org/torah-texts/7208442
   - Include the actual Sichos content about Mishkan vs Mikdash holiness

4. "DID YOU KNOW?" CARD (appears after Halacha 3):
   - Green-tinted background (rgba(29,185,84,0.15))
   - Info icon in green square
   - "Did You Know?" heading + fact about iron tools and the Altar

5. SHARE CTA at the bottom:
   - "Share today's learning with your community"
   - Green "Share Branded Card" button with share icon

Use the complete Hebrew text with nikud from the reference files. Every halacha block must have BOTH English and Hebrew.`,
      instructions: [
        'Read the existing mockup file and the reference files first',
        'Insert content into the below-fold section',
        'Use the exact Hebrew text with nikud from the reference',
        'Ensure bilingual layout: English LEFT, Hebrew RIGHT',
        'The sichos card pulsing dot should animate',
        'All cards should have proper rounded corners (20px) and spacing'
      ],
      outputFormat: 'JSON with keys: success, halachosAdded, cardsAdded'
    }
  },
  io: {
    inputJsonPath: `tasks/${taskCtx.effectId}/input.json`,
    outputJsonPath: `tasks/${taskCtx.effectId}/output.json`
  }
}));

const buildInteractionsTask = defineTask('build-interactions', (args, taskCtx) => ({
  kind: 'agent',
  title: 'Add voice overlay and all interactive elements',
  agent: {
    name: 'general-purpose',
    prompt: {
      role: 'Expert frontend developer specializing in interactive prototypes',
      task: `Edit the existing mockup at ${args.outputPath} to add the voice conversation overlay and ensure ALL elements are interactive.

ADD:

1. VOICE CONVERSATION OVERLAY (full-screen):
   - Covers entire viewport when activated
   - Background: rgba(12,12,12,0.94) with backdrop-filter: blur(30px)
   - Close X button (top-right)
   - Pulsing ring animation (120px circle, green border, expanding pulse behind it)
   - Microphone icon inside the ring (SVG)
   - "I'm Listening" heading (Plus Jakarta Sans, 24px, bold)
   - Prompt text: "Ask about Hilchos Beis HaBechirah"
   - Hebrew prompt: שאל על הלכות בית הבחירה (Noto Sans Hebrew, dimmed)
   - Animated audio waveform bars (5 green bars, varying heights, bounce animation)
   - "RETURN TO SHIUR" button (pill shape, elevated background)
   - Smooth fade-in/out transition (0.4s opacity)

2. ENSURE ALL INTERACTIONS WORK:
   - ✋ Raise Hand button → opens voice overlay
   - Close/Return to Shiur → closes voice overlay
   - Artifact dots → switch hero image (with crossfade)
   - Text toggle → show/hide karaoke overlay
   - Sichos card → opens chabad.org link in new tab
   - Timeline era pills → switch displayed image + update pill styles
   - All buttons: cursor:pointer, hover opacity change, active scale(0.97)
   - Touch feedback on mobile: touchstart → scale(0.97), touchend → scale(1)

3. BOTTOM NAV BAR (fixed):
   - 4 tabs: Home, Search, Saved, Profile
   - SVG icons + labels
   - Currently no tab is "active" (since we're in the player view)
   - Glass-morphism background
   - Safe area padding for notch devices

4. MINI-PLAYER BAR (hidden when full player is visible):
   - This is a placeholder — not visible in the player view
   - Include the HTML but set display:none`,
      instructions: [
        'Read the existing mockup file first',
        'Add the voice overlay HTML and its CSS',
        'Wire up all click handlers in the script section',
        'Ensure smooth transitions on all state changes',
        'Test that voice overlay opens from the hand button',
        'Include all animation keyframes'
      ],
      outputFormat: 'JSON with keys: success, interactionsAdded'
    }
  },
  io: {
    inputJsonPath: `tasks/${taskCtx.effectId}/input.json`,
    outputJsonPath: `tasks/${taskCtx.effectId}/output.json`
  }
}));

const polishAndVerifyTask = defineTask('polish-and-verify', (args, taskCtx) => ({
  kind: 'agent',
  title: 'Final polish, animations, and spec verification',
  agent: {
    name: 'general-purpose',
    prompt: {
      role: 'Senior frontend developer and QA engineer',
      task: `Review and polish the mockup at ${args.outputPath}. Also read the spec at ${args.specPath} (Section 3 and 5) to verify compliance.

POLISH TASKS:
1. Glass-morphism: Ensure top bar and bottom nav use backdrop-filter: blur(16px) with semi-transparent backgrounds
2. Transitions: All state changes should have smooth transitions (0.3s ease minimum)
3. Shadows: Add appropriate box-shadows to elevated elements (play button: green glow shadow, cards: subtle dark shadow)
4. Typography: Verify all text uses the correct font families, weights, and sizes per the design system
5. Spacing: Ensure consistent padding/margins (20px horizontal padding, 14px card gap, 24px section spacing)
6. Colors: Verify all colors match the spec exactly (#121212, #181818, #282828, #1DB954, etc.)
7. Border radius: 12px for small elements, 20px for cards/large elements
8. Responsive: Should look great at 375px width and scale reasonably to 768px
9. Animations:
   - Karaoke text auto-cycling (2.5s interval)
   - Artifact auto-cycling (5s interval)
   - Hand wave animation (2.5s, with 3s delay before first wave)
   - Sichos dot pulsing (2s)
   - Voice ring pulsing (2.5s)
   - Voice waveform bars (1s, staggered)

SPEC VERIFICATION CHECKLIST:
- [ ] Hero area is ~70vh
- [ ] Images from assets/ display properly
- [ ] Artifact indicator dots work
- [ ] Karaoke text is Hebrew, RTL, toggleable
- [ ] PiP video placeholder exists (top-left)
- [ ] Raise Hand button is same size as Play button
- [ ] Raise Hand has wave animation
- [ ] Bilingual layout: English LEFT, Hebrew RIGHT
- [ ] Sichos cards have pulsing green dot
- [ ] Sichos links to chabad.org
- [ ] Voice overlay has pulsing ring + waveform bars
- [ ] "Return to Shiur" button closes overlay
- [ ] Bottom nav has 4 tabs
- [ ] All fonts: Plus Jakarta Sans, DM Sans, Noto Sans Hebrew
- [ ] Dark theme colors match spec exactly

Fix any issues found. The mockup should feel like a premium, Spotify-level app.`,
      instructions: [
        'Read the current mockup file completely',
        'Read the spec file Sections 3 and 5',
        'Fix every issue found against the checklist',
        'Add any missing animations or transitions',
        'Ensure the file is valid HTML that opens correctly in a browser',
        'The final file should be polished and complete'
      ],
      outputFormat: 'JSON with keys: success, issuesFixed, checklistResults'
    }
  },
  io: {
    inputJsonPath: `tasks/${taskCtx.effectId}/input.json`,
    outputJsonPath: `tasks/${taskCtx.effectId}/output.json`
  }
}));
