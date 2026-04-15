# Phase 1.5 Scope — Merkos Rambam PWA

Consolidated scope for the Phase 1.5 "Interaction Layer" — the four features that turn the daily-content PWA from a reader into an interactive study tool.

Source of truth: `docs/PRODUCT_SPEC_FINAL.md` §6/§9, `docs/PHASE_2_3_SPEC.md` §3, issues #15–#18, and the process description at `.a5c/processes/phase-1-5-feature-delivery.process.md`.

---

## Ship order and rationale

1. **sefer-hamitzvos** (#18) — data-only read surface, no AI cost, lowest integration risk. Ships first to exercise the foundations PR end-to-end on a small blast radius.
2. **bookmarks** (#17) — device-scoped CRUD + offline mirror; proves the feature-flag middleware + IndexedDB offline pattern without touching the pipeline.
3. **quizzes** (#16) — first feature that exercises the pipeline → publisher bridge (new `quiz` artifact subtype + editorial review flow).
4. **raise-hand** (#15) — highest cost and risk (LLM spend, grounding-correctness, rate-limit policy). Ships last so foundations, flags, and editorial flow are all battle-tested before we turn on live LLM traffic.

Rationale: lowest risk first, highest cost and review burden last. Each feature ships behind a `phase_1_5_*` flag; production stays off until launch readiness approves.

---

## Features

### sefer-hamitzvos (#18)

**User story.** A daily Rambam learner on the Chabad track expects the corresponding Sefer Hamitzvos reference (positive/negative mitzvos) alongside each halacha. Today the app shows only the halachos — this card closes the gap.

**Acceptance criteria.**
- New Drizzle table `sefer_hamitzvos_reference` (canonical mapping: halacha → positive/negative mitzvah).
- Seed populated from a single source of truth (Sefaria index preferred; CSV fallback if coverage is insufficient).
- New content card rendered on homepage feed (via ContentFeed switch-on-contentType).
- Card shows mitzvah number, source text (Hebrew + English where available), and short description, RTL for Hebrew.
- Coverage validation: 50-row random sample manually reviewed before full seed; digitization error rate decides data source.
- Behind flag `phase_1_5_sefer_hamitzvos`.

**Data contract.**
```ts
sefer_hamitzvos_reference {
  id, sefer, perek, halacha_start, halacha_end,
  mitzvah_kind: 'positive' | 'negative',
  mitzvah_number: int,
  hebrew_text: text, english_text: text | null,
  source_ref: text,        // Sefaria-style canonical ref
  created_at, updated_at
}
```
Read endpoint: `GET /api/sefer-hamitzvos?sefer=&perek=&halacha=` returns the references attached to a daily unit. The homepage feed merges these into the existing content-item stream under a new `contentType: 'sefer_hamitzvos'`.

**Cut-lines vs Phase 2/3.**
- No editorial commentary on the mapping in v1 — display-only. Commentary extracted from shiurim is a Phase 2/Future concern.
- No user preferences for hiding the card in v1 — ships behind a global flag, not per-user.
- Hebrew-only / bilingual toggle deferred.

---

### bookmarks (#17)

**User story.** A learner wants to save today's "did you know" fact or a conceptual image to revisit offline (bus, Shabbos prep). The `/saved` tab — already stubbed in BottomNav — becomes functional.

**Acceptance criteria.**
- New Drizzle table `bookmark(device_id, content_item_id, created_at)` with composite uniqueness on `(device_id, content_item_id)`.
- `GET/POST/DELETE /api/bookmarks` scoped by `x-device-id` header (same pattern as `/api/preferences`).
- Bookmark toggle on every content card; optimistic UI.
- `/saved` route lists all bookmarked items, grouped by day.
- Offline: IndexedDB mirror of bookmarks + their underlying content items (service-worker cache) so `/saved` renders with zero network.
- Removing a bookmark instantly updates the list and the origin card's toggle state.
- Behind flag `phase_1_5_bookmarks`.
- Privacy-by-default: no user-entered notes in v1 (see cut-lines).

**Data contract.**
```ts
bookmark { device_id: text, content_item_id: int, created_at: timestamptz, PK: (device_id, content_item_id) }

GET    /api/bookmarks      -> { bookmarks: Bookmark[] }
POST   /api/bookmarks      { content_item_id }  -> 201 | 409 (already bookmarked)
DELETE /api/bookmarks/:id  -> 204
```

**Cut-lines vs Phase 2/3.**
- **No user-entered notes.** Privacy-by-default — we store only `(device_id, content_item_id)`. Notes re-scoped when product explicitly asks.
- No cross-device sync (anonymous `device_id` only, no login).
- No collections / folders / tags.
- No export.

---

### quizzes (#16)

**User story.** After reading the day's perek, a learner wants a quick comprehension check — multiple-choice questions grounded in the halachos just covered. Shown at the end of the content feed and via a dedicated `/quiz` route.

**Acceptance criteria.**
- Pipeline extension: new artifact subtype `quiz` with JSON schema `{ questions: [{ q, choices: string[], correct_idx: int, explanation: string }] }`.
- LLM generation via the Vercel AI Gateway (see Shared foundations) — prompts live in `pipeline/prompts/quiz.*`.
- Editorial review through the **existing artifact reviewer flow** (default — see open question #3); reviewer signs off before publication.
- Publisher patch: emit `quiz` artifacts to `content_items` with `contentType: 'quiz'`.
- Frontend: quiz card renders in the feed; `/quiz` route shows full-screen quiz mode (one question at a time, score summary, links back to referenced halachos).
- One quiz per perek per day (aligned to the 1-perek/3-perek track preference).
- Behind flag `phase_1_5_quizzes`.
- A11y: keyboard nav, screen-reader labels on choices, visible correct/incorrect state.

**Data contract.**
```ts
// Alembic: extend artifact_subtype enum with 'quiz'
artifact { subtype: 'quiz', payload: { questions: QuizQuestion[] } }
// Drizzle read side: content_items.contentType = 'quiz', payload flows through publisher
```

**Cut-lines vs Phase 2/3.**
- No leaderboards, no streak mechanics, no cross-day review (SRS / Chidon mode is explicitly on the Future list in spec §9).
- No per-user attempt history in v1 (device-scoped tracking deferred).
- No custom question authoring — LLM + editorial only.

---

### raise-hand (#15)

**User story.** While reading (and later listening to) a class, a learner taps the ✋ button to ask a question. The chatbot answers grounded in today's approved class content, knows where in the class the user is, and never leaks future material. Phase 1.5 is **text-only** chat per the issue; voice lands in Phase 3.

**Acceptance criteria.**
- `POST /api/chatbot/query` accepts `{ device_id, source_unit_id, current_ms, question }`, returns streamed assistant text.
- Context package respects the **timestamp cutoff invariant**: chatbot may only see transcript/halachot/artifacts up to `current_ms`. Enforced by context-builder + unit-test regression.
- Grounded in approved class content only (no generic web-scale Q&A).
- AI disclosure on every response; global kill-switch feature flag (`phase_1_5_raise_hand` → off = 503 + maintenance copy).
- Rate limit per `device_id` per day (tentative 20/day; see open question #2).
- Cost backstop: per-device monthly USD cap recorded via Gateway `providerMetadata.gateway.cost`.
- All interactions logged to `chatbot_sessions` (question, response, model, context tokens, active source unit, `device_id`).
- Streaming UI with word-level smoothing, mobile-keyboard-aware composer, stick-to-bottom behaviour.
- Structured error surface (offline / network_error / timeout / rate_limit) end-to-end.
- Behind flag `phase_1_5_raise_hand`.

**Data contract.**
```ts
chatbot_sessions {
  id, device_id, source_unit_id, playback_ms_at_query,
  question_text, response_text,
  llm_model, context_tokens_used, cost_usd,
  created_at
}
chatbot_messages { id, session_id, role, parts: jsonb, created_at }
device_spend     { device_id, month, usd_spent }   // backstop alongside daily count

POST /api/chatbot/query  -> text/event-stream (Vercel AI SDK chunks)
```

**Raise-Hand salvage plan (from `merkos-302/ai-chatbot` reuse inventory).**
Before writing anything net-new, the per-feature spec task lifts from the ai-chatbot repo:

- *Drop-in, use as-is:* `components/elements/*` (Streamdown response, reasoning accordion, `use-stick-to-bottom`, prompt-input, code-block, tool/task/loader); `lib/db/schema.ts` `Chat`/`Message_v2(parts json)`/`Vote_v2` as the Drizzle base (plus `device_id` column); `lib/errors.ts` `ChatSDKError` with per-surface visibility (port `Response.json` → Hono `c.json`); `lib/ai/providers.ts` `customProvider({ languageModels: gateway(id) })`; `lib/ai/models.ts` + `entitlements.ts`; `experimental_transform: smoothStream({ chunking: "word" })`; `streamText` + `stepCountIs(N)` + `experimental_activeTools` allowlist; `fetchWithErrorHandlers` (symmetric server/client error classifier); `hooks/use-visual-viewport.ts` (iOS keyboard height — must-have for PWA); `hooks/use-scroll-to-bottom.tsx` (SWR-as-imperative-trigger + observers); memoized `components/messages.tsx` + `experimental_throttle: 100`; typing-indicator gating on `status === "submitted"` OR streaming-with-no-visible-text.
- *Port with adapter:* rate-limit pattern (`getMessageCountByUserId` → `device_id`); cost tracking in `onFinish` (Gateway `providerMetadata.gateway.cost` → Postgres `device_spend`); `generateTitleFromUserMessage` (cheap-model title for `/saved` labels); mock language-model provider + `textToDeltas` streaming mock (zero-cost Playwright streaming tests — high-ROI); Playwright worker-scoped named-user fixtures remapped to `device_id`; client `onError` branch (rate-limit dialog vs toast).
- *Optional — response cache for user-agnostic answers:* small Postgres table keyed on `(source_unit_id, cutoff_ms_bucket, question_hash) → response` with 7-day TTL. Satisfies the "cache user-agnostic summaries" legacy pattern. Defer if Gateway cost + daily limit are sufficient.
- *Reference only (not Phase 1.5):* artifact/Document canvas, resumable streams (`Stream` table + Redis), WorkOS auth, Twilio/ElevenLabs/Composio, Helicone headers.

**Cut-lines vs Phase 2/3.**
- **No voice (STT/TTS).** Text-only, per issue #15 and spec §6 (voice is Phase 3).
- No chat history drawer / sidebar pagination in v1 (pattern earmarked for future — see Deferred follow-ups in the process doc).
- No resumable streams across page reloads in v1.
- No in-stream model-override pill.
- No cross-episode RAG — context is the single active source unit + transcript up to `current_ms`.

---

## Shared foundations (one PR before any feature)

Lands everything cross-cutting in a single PR so downstream feature branches never fight over migrations or provider wiring. Breakpoint: owner reviews migrations + cross-DB plan.

- **Drizzle migrations:** `bookmark`, `sefer_hamitzvos_reference`, `feature_flag` tables.
- **Alembic migrations:** `chatbot_sessions` table, `artifact_subtype` enum extended with `quiz`.
- **Publisher extension:** publish `quiz` artifacts to the web-read `content_items` surface.
- **Feature-flag middleware + `GET /api/flags`:** every new surface gated by a `phase_1_5_*` flag, resolved once per request.
- **Vercel AI SDK + Gateway wiring:** add `ai` + `@ai-sdk/gateway` dependencies in `api/`; swap `pipeline/src/pipeline/llm.py` to the Gateway OpenAI-compat base URL (~30-line change — the abstraction was already there); propagate `AI_GATEWAY_API_KEY` through `.env.example`, CDK secrets, and GitHub Actions deploy workflows. One billing surface for every LLM call in the project (chatbot + pipeline).

---

## Open questions — need owner answer at scope gate

1. **Sefer Hamitzvos data source** — Sefaria index vs manual CSV. Decide after the 50-row validation sample: if Sefaria coverage is >95 % clean, use it; otherwise fall back to a curated CSV.
2. **Raise-Hand rate limit** — per `device_id` per day. Tentative 20/day. Needs owner sign-off on the cost/UX trade-off.
3. **Quiz editorial cadence** — reuse the existing artifact reviewer flow (default: **yes**) or stand up a dedicated Telegram channel? Reusing is cheaper; a dedicated channel pays off only if quiz volume swamps image review.
4. **Vercel AI Gateway API key** — reuse the key the `ai-chatbot` project already uses under the Merkos Vercel team, or provision a fresh key + billing project for Rambam? Default: reuse, single bill. Both `api/` and `pipeline/` read `AI_GATEWAY_API_KEY`.

---

## Risks

- **Cost ceiling for raise-hand.** Too-loose a rate limit invites runaway Gateway spend; too tight kills UX. Mitigation: daily per-`device_id` count + monthly `device_spend` USD backstop + kill-switch flag.
- **Editorial burden scales with quizzes.** One quiz per perek per day means daily reviewer load grows with track adoption. Mitigation: reuse existing reviewer flow, monitor SLA, trigger the Telegram-channel option if reviewers back up.
- **Sefer Hamitzvos digitization quality.** Sefaria's index may be incomplete or inconsistently tagged for Chabad's mapping. Mitigation: 50-row validation sample before full seed; CSV fallback path prewired.
- **Gateway single-vendor concentration.** Consolidating all LLM spend on Vercel AI Gateway means one vendor outage hits both chatbot and pipeline. Mitigation: Gateway already routes across providers internally; kill-switch flag degrades gracefully; Helicone-style audit trail lives in our own Postgres (`chatbot_sessions`), not in the Gateway dashboard.

---

## Extracted patterns from legacy podcast plan

Cited from `/home/rayi/files/ChatGPT-Podcast_AI_Interaction_App.md`:

- **Timestamp cutoff invariant** — the chatbot sees only content up to the user's current playback position. Line **195** ("Only send ~1 minute of transcript (or a configurable window) around the current timestamp to the AI") and line **214** ("Indicate the user's current timestamp (and whether future transcript is included)"). Codified as a unit-test regression in the raise-hand feature.
- **Cache user-agnostic summaries** — responses that don't depend on user identity can be cached and reused. Line **153** ("We can cache metadata and summaries etc which are user agnostic as they are generated and apply to other users… that's just being cheap on tokens no big deal we can hold off on that for later on") and lines **256–258** ("Summaries, topic extractions, or clarifications that are user-agnostic can be cached. When another user asks the same question or wants a summary, fetch from cache if relevant"). Accepted as an optional v1 table (`(source_unit_id, cutoff_ms_bucket, question_hash) → response`); defer if Gateway + daily limit suffice.
- **Push-to-talk vs VoD** — the legacy plan contrasts voice-on-demand against explicit push-to-talk. Line **72** ("we'll of course have a push to talk if the user wants to not use vod"), lines **95–97** ("Voice-on-Demand (VoD) & Push-to-Talk Interaction — Users can interrupt playback using VoD. A push-to-talk button allows manual interaction if preferred"), and lines **202–207** ("Voice-on-Demand (VoD) … Push-to-Talk — An alternative to continuous VoD listening"). Phase 1.5 deliberately ships **neither** — text-only chat per issue #15; voice (either mode) is Phase 3.
- **Privacy by default** — anonymized logging, optional sharing only with explicit consent. Lines **260–267** ("Privacy Controls … Optionally share anonymized data with the podcaster or advertisers (with user consent)") and lines **314–339** ("Privacy & Compliance … The user's query (timestamp, question) may be recorded anonymously for analytics"). Manifested in Rambam as: chatbot logs keyed by `device_id` only; bookmarks store `(device_id, content_item_id)` with no user-entered notes in v1.

---

## Explicitly OUT of Phase 1.5 scope

- **Voice STT / TTS (Raise-Hand voice mode)** → Phase 3. Spec `PRODUCT_SPEC_FINAL.md` §6; `PHASE_2_3_SPEC.md` §3. Phase 1.5 delivers the text chat interface only.
- **Immersive player** (Main Zone / Artifact Tray / Text Panel / PiP) → Phase 2.
- **Rollout execution** → handed off to the post-launch-readiness process. This process ends at launch-package approval; the staged rollout is driven by the owner after that.
- **User-entered bookmark notes** → future. Privacy-by-default means v1 stores only `(device_id, content_item_id)`. Re-scope when product explicitly asks.
- **Async user-to-user messaging ("Think Out Loud" / Outlouding brand)** → not on roadmap. Flagged here to kill ambiguity; Phase 1.5's "interaction" means user ↔ content, never user ↔ user.
- **Telegram / WhatsApp review flow additions** beyond what already exists.
- **Helicone migration** — shipping with in-house audit (`chatbot_sessions` + future `/admin/chatbot/usage`) until the in-house view hurts.
- **Pipeline response caching** — out of v1; chatbot has its own cache table (optional).
- **Resumable chatbot streams** (Vercel AI SDK `Stream` table + Redis + `use-auto-resume`) — deferred until users complain about mid-stream PWA reloads.
- **Chat history drawer with date grouping** — pattern earmarked but not built in v1.
- **Header-aware RAG text chunker** — only relevant if we ever RAG over Rambam text; Phase 1.5 uses the live context package instead.
- **In-stream model-override pill** — only useful with budget-based model fallbacks, which v1 doesn't have.
