# CLAUDE.md — Merkos Rambam

## What this project is

A mobile-first PWA for daily Rambam learning. Serves AI-generated visual content (illustrations, infographics, charts), sichos references, perek overviews, and shareable assets. Built on the Merkos org starter template.

## Tech stack

- **API:** Hono + @hono/zod-openapi + Drizzle ORM + PostgreSQL (RDS)
- **Frontend:** React 19 + Vite 8 + TanStack Router + Tailwind v4 + openapi-react-query
- **Pipeline:** Python 3.11 + SQLAlchemy + Anthropic Claude + Replicate
- **Infra:** AWS CDK (ECS Fargate, RDS PostgreSQL 18, S3, CloudFront)
- **CI/CD:** GitHub Actions, pnpm workspaces

## Key commands

```bash
docker compose up -d                           # Start local PostgreSQL
pnpm --filter api run build                    # Build API
pnpm --filter frontend run build               # Build frontend
pnpm --filter api run test                     # Run API tests (TestContainers)
pnpm --filter frontend run test                # Run frontend tests
pnpm --filter api run kit generate             # Generate Drizzle migration
pnpm --filter frontend run codegen             # Regenerate typed API client
npx tsx --env-file=api/.env.dev api/scripts/seed-content.ts  # Seed sample data
```

## Project structure

- `api/src/routes/` — Hono route files (content, rambam, sichos, share, preferences, webhook)
- `api/src/schema/` — Drizzle ORM table definitions (6 tables)
- `frontend/src/routes/` — TanStack Router file-based routes
- `frontend/src/components/` — Content cards, layout, navigation, share
- `pipeline/src/pipeline/` — Python content generation modules (stubs, implementation pending)
- `infra/lib/` — AWS CDK constructs

## Conventions

- Routes use @hono/zod-openapi `createRoute` pattern with Zod schemas
- Frontend uses `font-[family-name:var(--font-ui)]` Tailwind syntax for CSS variable fonts
- Dark theme tokens in `frontend/src/styles/index.css` (Spotify-inspired)
- Hebrew content uses `dir="rtl"` on containers, not globally
- All content types render through ContentFeed switch-on-contentType pattern
- Schema ownership: Drizzle owns web tables, Alembic owns pipeline tables, same DB

## Content types

`perek_overview`, `conceptual_image`, `infographic`, `daily_chart`, `did_you_know`, `sichos_highlight`

## Branch strategy

`test` branch → staging deploy, `production` branch → production deploy. PRs use `/deploy` comment for preview environments.
