# Merkos Rambam — Next Steps

**Last updated:** April 13, 2026
**Last commit:** `6ae6a3c` — Initial scaffold (106 files, Increments 0–4)
**Repo:** https://github.com/rayistern/zajac (branch: `main`)

---

## Current State

The project has a fully scaffolded and building monorepo with:

- **API:** 6 implemented Hono routes, 6 Drizzle schema tables, Drizzle migration, seed script with 3 days of content
- **Frontend:** React + Vite + TanStack Router with 12 components (content cards, layout, navigation, share), dark theme, Hebrew fonts — builds to 90KB gzipped
- **Pipeline:** Python directory structure with 12 module stubs, config YAML, image style presets, Dockerfile
- **Infra:** AWS CDK from org starter template (VPC, RDS, ECS, CloudFront)
- **Docs:** Full README, CLAUDE.md, product spec (`/rambam/PRODUCT_SPEC_FINAL.md`)

Everything builds clean (`pnpm --filter api run build` + `pnpm --filter frontend run build`). No tests have been run yet (requires Docker for TestContainers).

---

## Resume on a New Machine

```bash
# 1. Clone
git clone https://github.com/rayistern/zajac.git merkos-rambam
cd merkos-rambam

# 2. Install pnpm
corepack enable && corepack prepare pnpm@10.32.1 --activate

# 3. Install dependencies
pnpm install

# 4. Verify builds
pnpm --filter api run build
pnpm --filter frontend run build

# 5. Start local dev (requires Docker)
docker compose up -d
cd api && node --env-file=.env.dev --import=tsx src/index.ts &
pnpm --filter frontend run dev

# 6. Seed the database
cd api && npx tsx --env-file=.env.dev scripts/seed-content.ts

# 7. Open http://localhost:5173
```

---

## Remaining Increments

### Inc 5: PWA + Offline (~1 day)

**What:** Make the app installable and cache content for offline use.

**Steps:**
1. Install `vite-plugin-pwa` in frontend:
   ```bash
   pnpm --filter frontend add -D vite-plugin-pwa
   ```
2. Add PWA plugin to `frontend/vite.config.ts` (see build plan for config)
3. Create app icons (192x192, 512x512) in `frontend/public/`
4. Configure Workbox runtime caching:
   - `StaleWhileRevalidate` for `/api/content/*`
   - `CacheFirst` for image assets
5. Add install prompt UI (optional banner)
6. Test: open on mobile Chrome → install prompt → works offline

**Files to modify:** `frontend/vite.config.ts`, `frontend/package.json`
**Files to create:** app icons in `frontend/public/`

---

### Inc 6: Content S3 + CDK (~1 day)

**What:** Serve content images from S3 via CloudFront instead of placeholder URLs.

**Steps:**
1. Create `infra/lib/components/content-storage.ts` — S3 bucket with CloudFront OAC
2. Update `infra/lib/components/frontend-distribution.ts` — add behaviors:
   - `/share/*` → API origin (for OG meta serving)
   - `/content-assets/*` → content S3 bucket
3. Update `infra/lib/infra-stack.ts` to wire the new constructs
4. Update seed script to upload images to S3
5. Update `imageUrl` in seed data to use CloudFront URLs
6. Deploy to staging: PR to `test` branch

**Files to create:** `infra/lib/components/content-storage.ts`
**Files to modify:** `infra/lib/infra-stack.ts`, `infra/lib/components/frontend-distribution.ts`, `api/scripts/seed-content.ts`

---

### Inc 7: Python Pipeline Implementation (~5 days) — CRITICAL PATH

**What:** Implement the full content generation pipeline. This is what makes the product real — automated content flowing from podcast RSS feeds into the database.

**The pipeline runs:** RSS → transcription → alignment → artifact planning → image generation → Telegram review → publication to DB

**Implementation order within the pipeline:**

#### 7a. Sefaria Client (`pipeline/src/pipeline/sefaria_client.py`)
- Fetch canonical Rambam text by Sefaria ref
- Cache in PostgreSQL (SQLAlchemy models in `db.py`)
- Parse hierarchy (works → books → chapters → halachot)

#### 7b. Dual Transcriber (`dual_transcriber.py`)
- sofer.ai API: accurate Hebrew text, no timestamps
- OpenAI Whisper API: word-level timestamps
- Merge: sofer.ai text + Whisper timestamps via SequenceMatcher

#### 7c. Text Aligner (`text_aligner.py`)
- **Pass 1:** Header detection — regex + LLM scan for "הלכה ט", "halacha 9"
- **Pass 2:** Gap detection — find missing halachot in sequence
- **Pass 3:** Content matching — semantic alignment of transcript → source units
- **Pass 4:** Verification — LLM holistic review + confidence scores
- All prompts in `pipeline/prompts/alignment_prompts.yaml` (to be created)

#### 7d. Artifact Planner (`artifact_planner.py`)
- LLM generates manifest per source unit: `[{type, subtype, priority, position, reason, prompt_focus}]`
- Checks existing artifacts to avoid duplicates
- Context modes: FULL (raw text) vs SYNTHESIZED (condensed by `context_synthesizer.py`)

#### 7e. Image Generator (`image_generator.py`)
- Execute planned artifacts via Replicate (Flux/SDXL) or DALL-E 3
- Style rotation from 5 presets in `prompts/image_system_prompt.yaml`
- Upload to S3, create `artifact_versions` records
- Prompt construction: base system prompt + style + context + prompt_focus

#### 7f. Telegram Poster + Vote Manager (`telegram_poster.py`, `vote_manager.py`)
- Post each generated image to Telegram voting group
- Track reactions (👍/👎) via webhook
- Tally votes on window close (24h default)
- Approve/reject based on thresholds (70% approval, min 3 votes)

#### 7g. Pipeline Orchestrator (`main.py`)
- Wire all stages together
- Configurable via `config.yaml`
- Structured logging with correlation IDs
- CLI entry point for manual runs

**Pipeline DB tables** (managed by Alembic, separate from Drizzle):
- Need to create SQLAlchemy models in `pipeline/src/pipeline/db.py` matching the schema in `MASTER_PLAN.md` §3
- Create Alembic migration directory + initial migration

**Environment variables needed:**
```
DATABASE_URL
SOFER_AI_API_KEY
OPENAI_API_KEY
ANTHROPIC_API_KEY
REPLICATE_API_TOKEN
TELEGRAM_BOT_TOKEN
TELEGRAM_VOTING_CHAT_ID
```

---

### Inc 8: WhatsApp Distribution (~2 days)

**What:** Daily automated WhatsApp delivery to subscribers.

**Steps:**
1. Implement `api/src/routes/webhook.ts` — handle Twilio inbound (subscribe/unsubscribe keywords)
2. Implement `pipeline/src/pipeline/whatsapp_sender.py`:
   - Query approved content items for today
   - Rate-limited Twilio sends (20/sec)
   - Retry with exponential backoff
   - Delivery tracking in `whatsapp_deliveries` table
3. Add subscriber management CLI commands to pipeline
4. Add EventBridge trigger for daily blast (CDK)

**Environment variables needed:**
```
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
WHATSAPP_PHONE_ID
```

---

### Inc 9: Polish + Production (~2 days)

**What:** Production readiness.

**Steps:**
1. **PostHog analytics:** Install `posthog-js` in frontend, wrap with provider, track: page views, content views, shares, track changes
2. **Sentry error tracking:** Install `@sentry/react` (frontend) + `@sentry/node` (API)
3. **Loading states:** Skeleton loaders for content feed, hero card
4. **Error states:** Friendly error messages with retry buttons
5. **Empty states:** "No content for today" with illustration
6. **Hebrew typography:** Fine-tune line-height, letter-spacing for Hebrew blocks
7. **Accessibility:** Focus management, ARIA labels, screen reader testing
8. **Performance:** WebP images, lazy loading audit, bundle size check
9. **Deploy:**
   - PR `main` → `test` (staging deploy)
   - Verify on staging
   - PR `test` → `production`

---

## Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | React + Vite (not Next.js) | Org starter template mandate |
| Hosting | ECS + CloudFront (not Vercel) | Org AWS CDK standard |
| Database | RDS PostgreSQL + Drizzle (not Supabase) | Org template, shared with pipeline |
| OG images | Satori in Hono route | Same lib Next.js uses, runs on ECS |
| Build order | Web platform first, pipeline second | Get a demo-able product fast, seed manually |
| Schema split | Drizzle (web tables) + Alembic (pipeline tables) | Non-overlapping ownership, same DB |
| Redis | Dropped for Phase 1 | PostgreSQL caching sufficient at this scale |

---

## Key Files Reference

| Purpose | Path |
|---------|------|
| API entry + routes | `api/src/app.ts` |
| Database schema | `api/src/schema/*.ts` |
| Content route (main query logic) | `api/src/routes/content.ts` |
| Sefaria proxy | `api/src/routes/rambam.ts` |
| Seed script | `api/scripts/seed-content.ts` |
| Frontend root layout | `frontend/src/routes/__root.tsx` |
| Homepage | `frontend/src/routes/index.tsx` |
| Content feed renderer | `frontend/src/components/content/ContentFeed.tsx` |
| Design tokens | `frontend/src/styles/index.css` |
| Pipeline config | `pipeline/config.yaml` |
| Image style presets | `pipeline/prompts/image_system_prompt.yaml` |
| CDK stack | `infra/lib/infra-stack.ts` |
| Build plan | `.claude/plans/deep-riding-curry.md` (local only) |
| Product spec | `/home/rayi/git/merkos/rambam/PRODUCT_SPEC_FINAL.md` |

---

## Spec Documents (in `/home/rayi/git/merkos/rambam/`)

These are the source-of-truth documents synthesized during this session:

| File | What |
|------|------|
| `PRODUCT_SPEC_FINAL.md` | Consolidated product spec (all 5 docs merged) |
| `merkos_rambam_prd_v3.md` | Original PRD |
| `merkos_rambam_trd_v1.md` | Original TRD |
| `MASTER_PLAN.md` | Pipeline implementation plan with full DB schema |
| `PHASE_2_3_SPEC.md` | Immersive player + voice chatbot spec |
| `merkos-rambam-frontend-spec.md` | Frontend UX brief |
| `mockup-v8.html` | HTML mockup — immersive player (2.3MB with embedded images) |
| `mockup-home.html` | HTML mockup — home/discovery screen (created this session) |
