# Merkos Rambam — Task List

**Last updated:** April 13, 2026

---

## Completed

- [x] **Inc 0: Project scaffold** — Monorepo with api, frontend, pipeline, infra workspaces (`6ae6a3c`)
- [x] **Inc 1: API routes** — 6 Hono routes (content, rambam, sichos, share, preferences, webhook), Drizzle schema (6 tables), seed script (`6ae6a3c`)
- [x] **Inc 2: Frontend components** — 12 React components (content cards, layout, navigation, share), dark theme, Hebrew fonts (`6ae6a3c`)
- [x] **Inc 3: Audio player** — HTML5 audio with MiniPlayer (Spotify-style), AudioPlayerProvider context (`6ae6a3c`)
- [x] **Inc 4: Share** — Web Share API with clipboard fallback, OG meta HTML endpoint (`6ae6a3c`)
- [x] **Inc 5: PWA + Offline** — vite-plugin-pwa, Workbox caching (API, images, fonts), app manifest, SVG icons (`4dbc1e2`)
- [x] **Inc 6: Content S3 + CDK** — S3 content bucket with CloudFront OAC, `/content-assets/*` behavior (`9523fe9`)
- [x] **Inc 7: Python pipeline** — 13 modules (RSS ingester, dual transcriber, 4-pass LLM aligner, context synthesizer, artifact planner, image generator, Telegram poster, vote manager, reconciliation, WhatsApp sender, orchestrator), 18 SQLAlchemy tables, Alembic, CLI with run/status subcommands (`d40ae5b`, `9523fe9`)
- [x] **Inc 8: WhatsApp webhook** — Twilio inbound handler: subscribe/unsubscribe/track change, TwiML responses, Hebrew keywords, phone hash storage (`4c27fd7`)
- [x] **Inc 9: Polish** — Skeleton loaders, error/empty states, ARIA labels, focus-visible, Hebrew typography, prefers-reduced-motion (`03b50e1`)
- [x] **PostHog analytics** — posthog-js in frontend, autocapture + pageviews, no-op without env var (`c20e350`)
- [x] **Sentry error tracking** — @sentry/react (frontend error boundary) + @sentry/node (API), no-op without DSN (`c20e350`)
- [x] **Org template compliance audit** — Verified 95%+ alignment with service-starter-template (`c70e533`)
- [x] **Test suites** — API: 5 test files (content, preferences, sichos, share, webhook); Frontend: 7 test files, 23 tests passing (`c70e533`)
- [x] **Spec docs committed** — PRODUCT_SPEC_FINAL, MASTER_PLAN, PHASE_2_3_SPEC, PRD v3, TRD v1, frontend spec, mockup-home (`d39b4b1`)

---

## In Progress / Next Up

### Validation & Testing

- [x] **Run API tests with Docker** — All 27 API tests pass with TestContainers (fixed preferences route bug and clearAll helper)
- [x] **Check coverage percentages** — API: 94.4% lines, Frontend: 90.21% lines (both pass 80% threshold)
- [x] **Add more tests if needed** — Expanded to 27 API + 61 frontend = 88 total tests

### Pipeline Smoke Test

- [x] **Install Python pipeline deps** — venv set up with all dependencies
- [x] **Create Alembic initial migration** — Hand-written migration (001), 18 tables with proper FK ordering and seed data
- [x] **Verify migration runs** — Applied successfully on Postgres 18 container, all 19 tables (18 + alembic_version) created, 4 artifact_types seeded
- [x] **Verify CLI works** — `status` and `run` commands work; fixed structlog config bug
- [ ] **Register a test RSS class** — Insert a Class record with an RSS feed URL (BLOCKED: need real RSS feed URL from Rayi)
- [ ] **Run pipeline end-to-end** — (BLOCKED: needs API keys for sofer.ai, OpenAI, Anthropic, Replicate)
- [ ] **Validate generated artifacts** — (BLOCKED: depends on end-to-end run)

### Infrastructure & Deployment

- [ ] **Set up AWS credentials** — Configure OIDC trust policy for GitHub Actions
- [ ] **Deploy CDK stack to staging** — `npx cdk deploy --context environmentName=staging`
- [ ] **Configure secrets** — Set API keys in AWS Secrets Manager or env vars (sofer.ai, OpenAI, Anthropic, Replicate, Telegram, Twilio)
- [ ] **Set frontend build env vars** — VITE_POSTHOG_KEY, VITE_SENTRY_DSN
- [ ] **Set API env vars** — SENTRY_DSN in ECS task definition
- [ ] **Custom domain + SSL** — ACM certificate, Route53 records, CloudFront alias
- [ ] **Push to staging** — Merge main → test branch, verify deploy-staging workflow runs
- [ ] **Push to production** — Merge test → production branch after staging validation

### Content & Editorial Setup

- [ ] **Create Telegram voting group** — Set up group, get chat ID, configure bot
- [ ] **Recruit editorial reviewers** — 6-10 volunteers for daily content review
- [ ] **Seed initial content** — Run `npx tsx --env-file=api/.env.dev api/scripts/seed-content.ts` with real content
- [ ] **Set up WhatsApp Business** — Twilio account, phone number, template messages

### GitHub Configuration

- [ ] **Create branch protections** — For `staging` and `production` branches (needs admin settings in GitHub UI)
- [x] **Create GitHub Environments** — All 5 created: production, staging, pr-preview, pr-preview-destroy, pr-deployment-change
- [x] **Create deployment branches** — staging, production, test branches created from main
- [x] **Configure Actions variables** — AWS_REGION set to us-east-1; DOMAIN_NAME and CLOUDFRONT_CERT_ARN need values from Rayi
- [ ] **Update CODEOWNERS** — Assign actual team members

---

## Future (Phase 1.5+)

- [ ] **Voice chatbot ("Raise Hand")** — STT → LLM → TTS, scoped to today's learning (Phase 1.5)
- [ ] **Quiz / review questions** — Per-perek questions generated by LLM (Phase 1.5)
- [ ] **Bookmarks / notes** — Save content items for later review (Phase 1.5)
- [ ] **Sefer Hamitzvos mapping** — Daily mitzvah cross-reference (Phase 1.5)
- [ ] **Immersive player** — Synced artifacts + source text + audio/video, Main Zone / Artifact Tray / Text Panel (Phase 2)
- [ ] **Full voice chatbot** — Context-aware, integrated into immersive player (Phase 3)
