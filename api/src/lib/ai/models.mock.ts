/**
 * Mock AI SDK language models — used when ``isTestEnvironment`` is true.
 *
 * This file is imported at top-level by ``providers.ts`` so it must not
 * pull in any devDependency. The previous version imported
 * ``MockLanguageModelV2`` from ``ai/test``, which transitively requires
 * ``msw`` — that's a devDep, stripped by the runtime Docker image's
 * ``pnpm deploy --prod``. On boot the production container would crash
 * with ``Cannot find package 'msw'``. So we hand-roll a ``LanguageModel``
 * that speaks the v2 spec, using only the runtime-safe ``ai`` main entry.
 *
 * Shape follows the merkos-302/ai-chatbot reference so Phase 1.5 features
 * (chatbot, summary) can share the same test harness.
 *
 * If a new logical model is added to ``providers.ts`` it MUST also be
 * added here (even as a near-duplicate of ``chatModel``) or the
 * test-branch ``customProvider`` will throw on unknown keys.
 *
 * Typing choice: we deliberately type ``createMockModel`` as ``any``.
 * The v2 ``LanguageModel`` interface is SDK-internal and moves between
 * versions; matching it structurally via ``@ai-sdk/provider`` types
 * would force a non-runtime dep into this file and couple the mock to a
 * moving contract. The SDK validates the shape at runtime, so the test
 * itself is the regression signal.
 */
import { simulateReadableStream } from "ai";

/**
 * Default "Mock response" stream — two word deltas with start/end/finish
 * frames. Kept inline (rather than imported from ``tests/prompts/utils``)
 * so this file has zero imports that cross ``rootDir: "src"``.
 *
 * Once the chatbot feature lands, branch on prompt contents here (or
 * delegate to ``tests/prompts/utils`` from a new test-only mock) to
 * produce distinguishable canned responses per test prompt.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const defaultStreamChunks = (): any[] => [
  { id: "mock-id", type: "text-start" },
  { id: "mock-id", type: "text-delta", delta: "Mock " },
  { id: "mock-id", type: "text-delta", delta: "response " },
  { id: "mock-id", type: "text-end" },
  {
    type: "finish",
    finishReason: "stop",
    usage: { inputTokens: 3, outputTokens: 10, totalTokens: 13 },
  },
];

interface MockOptions {
  /** Canned text returned from non-streaming ``doGenerate`` calls. */
  generateText: string;
  /**
   * Optional per-call override for streamed chunks. Falls back to
   * ``defaultStreamChunks`` so chat-style tests keep getting "Mock response".
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  streamChunks?: (prompt: unknown) => any[];
}

/**
 * Build a minimal ``LanguageModel`` (v2 spec) backed entirely by canned
 * data. Zero test-only deps so it's safe to ship in the production bundle.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const createMockModel = ({ generateText, streamChunks }: MockOptions): any => {
  return {
    specificationVersion: "v2",
    provider: "mock",
    modelId: "mock-model",
    defaultObjectGenerationMode: "tool",
    supportedUrls: [],
    supportsImageUrls: false,
    supportsStructuredOutputs: false,
    doGenerate: async () => ({
      rawCall: { rawPrompt: null, rawSettings: {} },
      finishReason: "stop",
      usage: { inputTokens: 10, outputTokens: 20, totalTokens: 30 },
      content: [{ type: "text", text: generateText }],
      warnings: [],
    }),
    doStream: async ({ prompt }: { prompt: unknown }) => ({
      stream: simulateReadableStream({
        chunkDelayInMs: 0,
        initialDelayInMs: 0,
        chunks: (streamChunks ?? defaultStreamChunks)(prompt),
      }),
      rawCall: { rawPrompt: null, rawSettings: {} },
    }),
  };
};

/** Default chat model — streams prompt-shaped responses for realistic tests. */
export const chatModel = createMockModel({
  generateText: "Hello, world!",
});

/**
 * Title/summary model — returns a short canned title.
 *
 * Kept as a separate mock so tests can assert that the right logical
 * model was selected (e.g. "we used ``title-model`` when summarising").
 */
export const titleModel = createMockModel({
  generateText: "This is a test title",
  streamChunks: () => [
    { id: "1", type: "text-start" },
    { id: "1", type: "text-delta", delta: "This is a test title" },
    { id: "1", type: "text-end" },
    {
      type: "finish",
      finishReason: "stop",
      usage: { inputTokens: 3, outputTokens: 10, totalTokens: 13 },
    },
  ],
});
