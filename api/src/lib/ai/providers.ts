/**
 * Vercel AI SDK provider setup — Phase 1.5 foundations.
 *
 * Traffic routing:
 *   prod/dev → Vercel AI Gateway (``AI_GATEWAY_API_KEY``) → upstream model
 *   test     → local mock provider, so no network/API-key/cost during CI
 *
 * How to use from a route handler:
 *
 *   import { myProvider } from "../lib/ai/providers";
 *   const { textStream } = await streamText({
 *     model: myProvider.languageModel("chat-model"),
 *     messages,
 *   });
 *
 * Why a fixed logical model id (``chat-model``) instead of the raw gateway
 * id (``anthropic/claude-sonnet-4.6``)?
 *   1. The mock provider has to register the same key so test and prod
 *      share an API surface.
 *   2. It keeps handler code stable when we swap underlying models.
 *   3. We can fan out (e.g. a cheap ``title-model`` vs. a strong
 *      ``chat-model``) without touching handlers.
 *
 * Adding a new logical model:
 *   - add an entry under ``languageModels`` in BOTH branches below
 *   - keep test-branch models minimal (a mock of the real thing, not a second
 *     real call)
 */
import { createGateway } from "@ai-sdk/gateway";
import { customProvider } from "ai";
import { chatModel as mockChatModel, titleModel as mockTitleModel } from "./models.mock";

// Detect test mode the same way the rest of the test infra does
// (``api/tests/setup.ts`` sets ``NODE_ENV=test`` via vitest).
export const isTestEnvironment =
  process.env.NODE_ENV === "test" || process.env.VITEST === "true";

// Gateway instance — reads ``AI_GATEWAY_API_KEY`` from the process env.
// We build it lazily-at-import-time so production containers pick up the
// Secrets Manager-injected value on boot.
const gateway = createGateway({
  apiKey: process.env.AI_GATEWAY_API_KEY,
});

// Export so advanced handlers (e.g. per-request provider options, model
// discovery) can reach the raw gateway when needed.
export { gateway };

/**
 * ``myProvider`` is the single entry point routes should use.
 *
 * In tests it resolves to a mock provider that streams canned chunks; in
 * all other environments it resolves to the Vercel AI Gateway instance.
 *
 * Note on imports: we top-level-import ``models.mock`` rather than
 * lazy-loading it. The mock hand-rolls a ``LanguageModel`` from
 * runtime-safe pieces of the ``ai`` main entry (no ``ai/test``, no
 * ``msw``) so it's harmless to ship in the production image — the
 * ``isTestEnvironment`` branch simply never invokes it.
 */
export const myProvider = isTestEnvironment
  ? customProvider({
      languageModels: {
        "chat-model": mockChatModel,
        "title-model": mockTitleModel,
      },
    })
  : customProvider({
      languageModels: {
        // Chatbot workhorse. Sonnet 4.6 = good quality, reasonable cost,
        // native tool-calling (we'll need it for the bookmark/quiz chat).
        "chat-model": gateway("anthropic/claude-sonnet-4.6"),
        // Cheap + fast — used for summarising/labelling rather than chatting.
        "title-model": gateway("openai/gpt-5-mini"),
      },
    });
