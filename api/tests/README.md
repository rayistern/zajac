# api/tests

## Running

```bash
pnpm --filter api run test
```

A disposable PostgreSQL 18 container is spun up per test run via
TestContainers (see `setup.ts`). Nothing is shared with your local
`docker compose` stack.

## Mocked AI models

Anything going through the Vercel AI Gateway in production
(`src/lib/ai/providers.ts`) is swapped for in-process mocks during tests.
The switch is driven by `isTestEnvironment` — which is true whenever
`NODE_ENV=test` or `VITEST=true`, both of which Vitest sets for you.

### Files involved

- `src/lib/ai/providers.ts` — exports `myProvider`. In test mode it
  returns a `customProvider` wired up to the mocks below; in prod it
  returns a `customProvider` wired up to `gateway("anthropic/…")`, etc.
- `src/lib/ai/models.mock.ts` — the mock `LanguageModelV2` instances.
  Built on top of `MockLanguageModelV2` from `ai/test` so they speak the
  exact v2 protocol the rest of the SDK expects.
- `tests/prompts/utils.ts` — helpers for building mock stream chunks
  (`textToDeltas`, `getResponseChunksByPrompt`). This file is the
  canonical place to add prompt-specific canned responses as we grow
  the chatbot test suite.

### Adding a new logical model

1. Add an entry to **both** branches of `customProvider({ languageModels })`
   in `providers.ts` — the logical id must be identical in test and prod.
2. Export a new `MockLanguageModelV2` in `models.mock.ts` and register
   it in the test branch.
3. Add at least one regression test asserting both `doGenerate` and
   `doStream` paths work (see `tests/providers.test.ts`).

### Adding a canned prompt response

`getResponseChunksByPrompt(prompt)` currently returns one default
response for every prompt. When a feature needs branching (e.g. the
chatbot needs different responses for different user questions), copy
the `compareMessages` + `TEST_PROMPTS` pattern from the upstream
`merkos-302/ai-chatbot` repo — the shape is intentionally identical so
those fixtures port 1:1.

## Why not hit the real gateway?

- **Cost** — CI runs on every PR; a single leak to prod pricing gets
  expensive fast.
- **Flakiness** — gateway timeouts surface as red builds even when the
  code is fine.
- **Secrets** — `AI_GATEWAY_API_KEY` shouldn't need to exist in the test
  environment at all.

If you ever need a live integration test, put it under a separate
`pnpm run test:integration` script guarded by an env var; do not
relax the default path.
