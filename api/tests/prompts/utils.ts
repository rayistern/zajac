/**
 * Test-side helpers for building mock streams the AI SDK will accept.
 *
 * Kept intentionally tiny — the reference ai-chatbot repo has a much
 * larger copy with branching on named prompts (USER_SKY, USER_GRASS, …)
 * because its Playwright suite asserts exact streamed responses. We'll
 * grow this file with those fixtures as we land the chatbot feature;
 * for now we only need enough to satisfy ``models.mock`` and unit
 * tests that round-trip a single prompt.
 */
import type { LanguageModelV2StreamPart } from "@ai-sdk/provider";
import { generateId, type ModelMessage } from "ai";

/**
 * Turn a free-form string into a sequence of ``text-delta`` chunks,
 * bookended by ``text-start``/``text-end``. This is the happy-path
 * shape the AI SDK client expects for streamed text responses.
 *
 * Usage inside a mock's ``doStream``:
 *
 *   chunks: [
 *     ...textToDeltas("Hello there"),
 *     { type: "finish", finishReason: "stop", usage: {...} },
 *   ]
 */
export const textToDeltas = (text: string): LanguageModelV2StreamPart[] => {
  const id = generateId();
  const deltas = text.split(" ").map((word) => ({
    id,
    type: "text-delta" as const,
    delta: `${word} `,
  }));
  return [{ id, type: "text-start" }, ...deltas, { id, type: "text-end" }];
};

/**
 * Default prompt-to-chunks resolver used by ``chatModel`` in
 * ``models.mock.ts``. Returns a canned response so tests don't have to
 * stub the model per-call.
 *
 * Once the chatbot feature lands we'll grow this to branch on message
 * content (mirror ai-chatbot's ``compareMessages`` + ``TEST_PROMPTS``
 * pattern) so different test prompts produce deterministic but
 * distinguishable responses.
 */
export const getResponseChunksByPrompt = (
  _prompt: ModelMessage[],
): LanguageModelV2StreamPart[] => {
  return [
    ...textToDeltas("Mock response"),
    {
      type: "finish",
      finishReason: "stop",
      usage: { inputTokens: 3, outputTokens: 10, totalTokens: 13 },
    },
  ];
};
