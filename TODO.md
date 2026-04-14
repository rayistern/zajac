# Merkos Rambam — Task List

> 🟢 **Active tracking has moved to GitHub Issues:** https://github.com/rayistern/zajac/issues
>
> This file is kept as a historical record of completed increments. Open work lives in issues.

---

## Completed Increments

- [x] **Inc 0: Project scaffold** — Monorepo with api, frontend, pipeline, infra workspaces (`6ae6a3c`)
- [x] **Inc 1: API routes** — 6 Hono routes, Drizzle schema (6 tables), seed script (`6ae6a3c`)
- [x] **Inc 2: Frontend components** — 12 React components, dark theme, Hebrew fonts (`6ae6a3c`)
- [x] **Inc 3: Audio player** — HTML5 audio with MiniPlayer (Spotify-style), AudioPlayerProvider context (`6ae6a3c`)
- [x] **Inc 4: Share** — Web Share API with clipboard fallback, OG meta HTML endpoint (`6ae6a3c`)
- [x] **Inc 5: PWA + Offline** — vite-plugin-pwa, Workbox caching, app manifest (`4dbc1e2`)
- [x] **Inc 6: Content S3 + CDK** — S3 content bucket with CloudFront OAC (`9523fe9`)
- [x] **Inc 7: Python pipeline** — 13 modules, 18 SQLAlchemy tables, Alembic, CLI (`d40ae5b`, `9523fe9`)
- [x] **Inc 8: WhatsApp webhook** — Twilio inbound handler with Hebrew keywords (`4c27fd7`)
- [x] **Inc 9: Polish** — Skeleton loaders, error/empty states, ARIA, Hebrew typography (`03b50e1`)
- [x] **PostHog + Sentry** — Analytics + error tracking, no-op without env vars (`c20e350`)
- [x] **Org template compliance** — 95%+ aligned with service-starter-template (`c70e533`)
- [x] **Test suites** — 27 API + 61 frontend + 68 pipeline = 156 tests, coverage 94.4%/90.2% (`c70e533`, `a344585`)
- [x] **OpenRouter integration** — Single key routes LLM, images, and LLM-based audio (`7490229`, `e517ea0`)
- [x] **Demo launcher** — `./scripts/demo.sh` one-command local stack (`a082964`)
- [x] **Alembic migration** — Pipeline tables deployable via `alembic upgrade` (`ab0bd16`)
- [x] **Sefaria end-to-end** — Fetched 27 real Rambam halachot (Marriage 2), synthesized to English via Claude
- [x] **Image gen end-to-end** — Generated watercolor illustration via OpenRouter Gemini (2MB PNG in ~8s)
- [x] **GitHub environments** — All 5 envs created (production, staging, pr-preview, pr-preview-destroy, pr-deployment-change)
- [x] **GitHub Issues migrated** — All open tasks now tracked at https://github.com/rayistern/zajac/issues

---

## Where to go for open work

- **Active issues:** https://github.com/rayistern/zajac/issues
- **Labels:**
  - `pipeline` — content generation pipeline
  - `api` — Hono backend
  - `frontend` — React PWA
  - `infra` — AWS CDK + GitHub Actions
  - `testing` — test coverage, CI
  - `content` — editorial, WhatsApp, seed data
  - `blocked` — waiting on external dependency (AWS creds, API keys, team input)
  - `deferred` — intentionally postponed for later phases
  - `phase-1.5` / `phase-2` — future work aligned with product spec phases
