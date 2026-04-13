# Merkos Rambam

A mobile-first Progressive Web App for daily Rambam learning with AI-generated visual content, sichos references, audio playback, and shareable assets.

**Owner:** Rayi Stern / Merkos 302 / ChabadAI

---

## Quick Start

```bash
# Prerequisites: Node.js 20+, pnpm 10+, Docker

# 1. Start local PostgreSQL
docker compose up -d

# 2. Install dependencies
pnpm install

# 3. Generate database migration (if schema changed)
pnpm --filter api run kit generate

# 4. Start API (port 3000)
cd api && node --env-file=.env.dev --import=tsx src/index.ts

# 5. Start frontend (port 5173, proxies /api/* to :3000)
pnpm --filter frontend run dev

# 6. Seed sample content (requires running DB)
cd api && npx tsx --env-file=.env.dev scripts/seed-content.ts
```

The app will be available at `http://localhost:5173`.

---

## Architecture

```
merkos-rambam/
├── api/          # Hono API server (TypeScript)
├── frontend/     # React + Vite SPA (TypeScript)
├── pipeline/     # Content generation pipeline (Python)
├── infra/        # AWS CDK infrastructure
└── .github/      # CI/CD workflows
```

### Tech Stack

| Layer | Technology |
|---|---|
| API Framework | Hono + @hono/zod-openapi |
| ORM | Drizzle ORM (PostgreSQL) |
| Frontend | React 19 + Vite 8 + TanStack Router |
| Data Fetching | openapi-react-query (TanStack Query) |
| Styling | Tailwind CSS v4 |
| Pipeline | Python 3.11 + SQLAlchemy + Anthropic Claude |
| Infrastructure | AWS CDK (ECS Fargate, RDS, S3, CloudFront) |
| CI/CD | GitHub Actions with AWS OIDC |
| Testing | Vitest + TestContainers (API), Vitest + Testing Library (frontend) |

### System Flow

```
RSS Feeds → Dual Transcription → LLM Alignment → Artifact Planning
    → Image Generation → Telegram Voting → WhatsApp Distribution
                                              ↓
                            PostgreSQL (shared DB)
                                              ↓
                    Hono API → React Frontend (PWA)
```

---

## Project Structure

### API (`api/`)

```
api/src/
  app.ts                    # Route composition + OpenAPI doc
  db.ts                     # Drizzle + pg pool
  env.ts                    # Zod env validation
  index.ts                  # Server entry point
  routes/
    content.ts              # GET /api/content/today, /day/:date, /item/:id
    rambam.ts               # GET /api/rambam/:sefer/:perek/:halacha (Sefaria proxy)
    sichos.ts               # GET /api/sichos/:sefer/:perek
    preferences.ts          # GET/PUT /api/preferences (by x-device-id header)
    share.ts                # GET /api/share/:contentId/meta (OG meta HTML)
    webhook.ts              # POST /api/webhook/whatsapp (Twilio)
  schema/
    learning-days.ts        # Daily schedule (date → perakim per track)
    content-items.ts        # All generated content (images, overviews, etc.)
    sichos-references.ts    # Rebbe's sichos mapped to halachot
    user-preferences.ts     # Anonymous track preference
    whatsapp.ts             # Subscriber list
    share-events.ts         # Share analytics
    index.ts                # Barrel export
api/scripts/
  seed-content.ts           # Seed 3 days of sample content
api/tests/
  setup.ts                  # TestContainers PostgreSQL
  helpers.ts                # Transaction rollback + table clear
  endpoint.test.ts          # Health check test
  user-roles.test.ts        # Schema query tests
```

### Frontend (`frontend/`)

```
frontend/src/
  main.tsx                  # React root with QueryClient + Router
  client.ts                 # openapi-fetch + openapi-react-query client
  routes/
    __root.tsx              # Root layout: AudioPlayer, MiniPlayer, BottomNav
    index.tsx               # Homepage: hero, track selector, content feed, sichos
    day.$date.tsx           # Day-specific content view
  components/
    content/
      ContentFeed.tsx       # Renders items by contentType (switch/map)
      PerekOverview.tsx     # Text card — perek summary
      ConceptualImage.tsx   # Image card with badge + share button
      Infographic.tsx       # Image card (blue badge)
      DailyChart.tsx        # Chart image card (green badge)
      DidYouKnow.tsx        # Purple insight card
      SichosHighlight.tsx   # Gold-accented Rebbe's insight card
    layout/
      MiniPlayer.tsx        # Fixed bottom audio bar (Spotify-style)
      BottomNav.tsx         # Home / Search / Saved tabs
    navigation/
      TrackSelector.tsx     # 1-perek / 3-perek toggle
      DayNavigator.tsx      # Prev/next day arrows
    share/
      ShareButton.tsx       # Web Share API with clipboard fallback
  hooks/
    useTrack.ts             # Track preference (localStorage)
    useAudioPlayer.ts       # Audio context + HTML5 audio element
  styles/
    index.css               # Tailwind v4 + design tokens (dark theme)
```

### Pipeline (`pipeline/`)

```
pipeline/
  pyproject.toml            # Python deps (anthropic, replicate, telegram, twilio)
  Dockerfile
  config.yaml               # All pipeline settings (models, styles, thresholds)
  src/pipeline/
    main.py                 # Orchestrator entry point
    config.py               # Config loader
    db.py                   # SQLAlchemy models (mirrors Drizzle schema)
    sefaria_client.py       # Fetch + cache canonical Rambam text
    dual_transcriber.py     # sofer.ai (accuracy) + Whisper (timestamps) → merge
    text_aligner.py         # 4-pass LLM alignment (headers → gaps → content → verify)
    artifact_planner.py     # LLM plans artifacts per source unit
    context_synthesizer.py  # FULL vs SYNTHESIZED context for image prompts
    image_generator.py      # Replicate/DALL-E with style rotation
    telegram_poster.py      # Post to voting group for review
    vote_manager.py         # Tally votes, approve/reject
    whatsapp_sender.py      # Rate-limited Twilio distribution
    reconciliation.py       # LLM audits for stale/orphaned artifacts
  prompts/
    image_system_prompt.yaml  # 5 art styles (photorealistic, watercolor, etc.)
```

### Infrastructure (`infra/`)

```
infra/
  bin/infra.ts              # CDK app entry
  lib/
    infra-stack.ts          # Main stack (VPC, RDS, ECS, CloudFront)
    components/
      database.ts           # RDS PostgreSQL 18 construct
      frontend-distribution.ts  # S3 + CloudFront
      stage-utils.ts        # Environment-specific config
```

---

## API Reference

All routes serve OpenAPI docs at `GET /doc`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/api/content/today?track=3-perek` | Today's published content for track |
| `GET` | `/api/content/day/:date?track=3-perek` | Content for specific date |
| `GET` | `/api/content/item/:id` | Single content item by UUID |
| `GET` | `/api/rambam/:sefer/:perek` | Perek text from Sefaria (cached proxy) |
| `GET` | `/api/rambam/:sefer/:perek/:halacha` | Single halacha text |
| `GET` | `/api/sichos/:sefer/:perek` | Sichos references for a perek |
| `GET` | `/api/share/:contentId/meta` | HTML page with OG meta tags for social sharing |
| `GET` | `/api/preferences` | Get user preferences (by `x-device-id` header) |
| `PUT` | `/api/preferences` | Update track preference |
| `POST` | `/api/webhook/whatsapp` | Twilio inbound webhook |

---

## Database Schema

Six web-facing tables managed by Drizzle ORM:

| Table | Purpose |
|-------|---------|
| `learning_day` | Daily schedule — date, Hebrew date, perakim per track (JSONB) |
| `content_item` | All generated content — type, sefer/perek/halacha, title, content (JSONB), image URL, editorial status |
| `sichos_reference` | Rebbe's sichos mapped to individual halachot |
| `user_preference` | Anonymous device-id → track preference |
| `whatsapp_subscriber` | Subscriber phone hash, track, status |
| `share_event` | Share analytics (content item + platform) |

Pipeline tables (managed by Alembic, same database):

| Table | Purpose |
|-------|---------|
| `works`, `source_units` | Canonical Torah texts from Sefaria |
| `classes`, `episodes` | Podcast RSS feeds and episodes |
| `transcripts`, `alignments` | Dual transcription + LLM alignment |
| `artifact_plans`, `artifacts`, `artifact_versions` | Generated content lifecycle |
| `vote_sessions`, `votes`, `edit_requests` | Telegram editorial workflow |
| `whatsapp_deliveries` | Delivery tracking |

Generate a new migration after schema changes:

```bash
pnpm --filter api run kit generate
```

---

## Content Types

| Type | Description | Badge Color |
|------|-------------|-------------|
| `perek_overview` | AI-generated perek summary | — (text card) |
| `conceptual_image` | AI illustration of a halacha | Green |
| `infographic` | Flowchart, timeline, or comparison | Blue |
| `daily_chart` | Visual chart from day's content | Teal |
| `did_you_know` | Single compelling fact | Purple |
| `sichos_highlight` | Rebbe's sichos reference | Gold |

All AI-generated content passes through human editorial review (Telegram voting group) before publication.

---

## Design System

Dark theme inspired by Spotify. Design tokens defined in `frontend/src/styles/index.css`:

| Token | Value | Usage |
|-------|-------|-------|
| `--bg` | `#121212` | Page background |
| `--surface` | `#181818` | Card backgrounds |
| `--elevated` | `#282828` | Raised elements |
| `--green` | `#1DB954` | Primary accent (CTAs, active states) |
| `--gold` | `#C5A059` | Sichos/Rebbe's insights |
| `--grey` | `#B3B3B3` | Secondary text |
| `--grey-dim` | `#535353` | Tertiary text |
| `--font-ui` | Plus Jakarta Sans | Headings, labels, badges |
| `--font-body` | DM Sans | Body text, descriptions |
| `--font-hebrew` | Noto Sans Hebrew | Hebrew/RTL content |

The mockup-v8.html in the `/rambam` spec directory is the reference design for the immersive player (Phase 2). The mockup-home.html is the reference for the home screen.

---

## Development

### Prerequisites

- Node.js 20+ (via nvm)
- pnpm 10+ (via corepack: `corepack enable && corepack prepare pnpm@10.32.1 --activate`)
- Docker (for local PostgreSQL and TestContainers)
- Python 3.11+ (for pipeline development)

### Local Development

```bash
# Terminal 1: Database
docker compose up -d

# Terminal 2: API
cd api && node --env-file=.env.dev --import=tsx src/index.ts

# Terminal 3: Frontend
pnpm --filter frontend run dev
```

The Vite dev server proxies `/api/*` to `http://localhost:3000`.

### Testing

```bash
# API integration tests (spins up TestContainers PostgreSQL)
pnpm --filter api run test

# Frontend unit tests
pnpm --filter frontend run test

# Coverage check (80% threshold)
pnpm run coverage:check
```

### Building

```bash
# API (TypeScript → dist/)
pnpm --filter api run build

# Frontend (Vite → dist/)
pnpm --filter frontend run build
```

### Frontend Codegen

After changing API routes, regenerate the typed client:

```bash
# Start API first, then:
pnpm --filter frontend run codegen
```

This generates `frontend/src/types/backend-schema.d.ts` from the OpenAPI spec at `/doc`.

---

## Deployment

### Branch Strategy

| Branch | Environment | Trigger |
|--------|-------------|---------|
| `test` | Staging | Push triggers `deploy-staging.yaml` |
| `production` | Production | Push triggers `deploy-production.yaml` |
| PR branches | Preview | `/deploy` comment triggers `deploy-pr-preview.yaml` |

### GitHub Actions Workflows

| Workflow | Purpose |
|----------|---------|
| `coverage-check.yaml` | PR gate — 80% statement coverage for api + frontend |
| `deploy-staging.yaml` | Build + deploy to staging on push to `test` |
| `deploy-production.yaml` | Build + deploy to production on push to `production` |
| `deploy-pr-preview.yaml` | Preview environments via `/deploy` comment |
| `branch-merge-gate.yaml` | Branch protection enforcement |

### Infrastructure Changes

Changes to `infra/` require `@infra-team` approval via CODEOWNERS. For PR previews, infra changes additionally require a `/approve` comment.

### Setup Checklist

1. [ ] Update `.github/CODEOWNERS` with team assignments
2. [ ] Create branch protections for `test` and `production`
3. [ ] Create GitHub Environments: `production`, `staging`, `pr-preview`, `pr-preview-destroy`, `pr-deployment-change`
4. [ ] Configure Actions variables: `AWS_REGION`, `DOMAIN_NAME`, `CLOUDFRONT_CERT_ARN`
5. [ ] Add repository to AWS GitHub OIDC trust policy
6. [ ] Configure custom domain + ACM certificate

---

## Phased Delivery

| Phase | Status | Description |
|-------|--------|-------------|
| **0** | Pre-build | Content validation via WhatsApp (no app) |
| **1** | **In progress** | Core platform — content feed, audio, sharing, WhatsApp |
| **1.5** | Planned | Voice chatbot, quizzes, bookmarks |
| **2** | Planned | Immersive player (synced artifacts + source text + audio/video) |
| **3** | Planned | Voice chatbot integrated into player |

Full product spec: `/home/rayi/git/merkos/rambam/PRODUCT_SPEC_FINAL.md`
Build plan: `/home/rayi/.claude/plans/deep-riding-curry.md`

---

## Related Documents

| Document | Location |
|----------|----------|
| Product Spec (consolidated) | `/rambam/PRODUCT_SPEC_FINAL.md` |
| PRD v3 | `/rambam/merkos_rambam_prd_v3.md` |
| TRD v1 | `/rambam/merkos_rambam_trd_v1.md` |
| Master Implementation Plan | `/rambam/MASTER_PLAN.md` |
| Phase 2/3 Spec | `/rambam/PHASE_2_3_SPEC.md` |
| Frontend Mockup (Player) | `/rambam/mockup-v8.html` |
| Frontend Mockup (Home) | `/rambam/mockup-home.html` |
| Org Deployment Workflow | `Merkos Development Workflows (Deployment Flow).md` |
| Org Starter Template | `/service-starter-template/` |
