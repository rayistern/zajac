/**
 * Mock AI SDK language models — used when ``isTestEnvironment`` is true.
 *
 * Why port this from merkos-302/ai-chatbot?
 *   - Tests must never hit the real gateway (cost, flakiness, auth).
 *   - ``@ai-sdk/ai/test`` ships ``MockLanguageModelV2`` which speaks the
 *     exact v2 spec the rest of the SDK expects, so we don't have to
 *     hand-roll a stub matching a moving internal contract.
 *   - Shape kept identical to the ai-chatbot reference so future Phase 1.5
 *     features (chatbot, summary) can run against the same test harness
 *     the reference app uses.
 *
 * If a new logical model is added to ``providers.ts`` it MUST also be
 * added here (even as a near-duplicate of ``chatModel``) or the
 * test-branch ``customProvider`` will throw on unknown keys.
 */
import { simulateReadableStream } from "ai";
import { MockLanguageModelV2 } from "ai/test";
import { getResponseChunksByPrompt } from "../../../tests/prompts/utils";

/** Default chat model — streams prompt-shaped responses for realistic tests. */
export const chatModel = new MockLanguageModelV2({
  doGenerate: async () => ({
    rawCall: { rawPrompt: null, rawSettings: {} },
    finishReason: "stop",
    usage: { inputTokens: 10, outputTokens: 20, totalTokens: 30 },
    content: [{ type: "text", text: "Hello, world!" }],
    warnings: [],
  }),
  doStream: async ({ prompt }) => ({
    stream: simulateReadableStream({
      chunkDelayInMs: 0,
      initialDelayInMs: 0,
      chunks: getResponseChunksByPrompt(prompt),
    }),
    rawCall: { rawPrompt: null, rawSettings: {} },
  }),
});

/**
 * Title/summary model — returns a short canned title.
 *
 * Kept as a separate mock so tests can assert that the right logical
 * model was selected (e.g. "we used ``title-model`` when summarising").
 */
export const titleModel = new MockLanguageModelV2({
  doGenerate: async () => ({
    rawCall: { rawPrompt: null, rawSettings: {} },
    finishReason: "stop",
    usage: { inputTokens: 10, outputTokens: 20, totalTokens: 30 },
    content: [{ type: "text", text: "This is a test title" }],
    warnings: [],
  }),
  doStream: async () => ({
    stream: simulateReadableStream({
      chunkDelayInMs: 0,
      initialDelayInMs: 0,
      chunks: [
        { id: "1", type: "text-start" },
        { id: "1", type: "text-delta", delta: "This is a test title" },
        { id: "1", type: "text-end" },
        {
          type: "finish",
          finishReason: "stop",
          usage: { inputTokens: 3, outputTokens: 10, totalTokens: 13 },
        },
      ],
    }),
    rawCall: { rawPrompt: null, rawSettings: {} },
  }),
});
