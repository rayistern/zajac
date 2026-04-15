import { describe, expect, test } from "vitest";
import { streamText, generateText } from "ai";
import { myProvider, isTestEnvironment } from "../src/lib/ai/providers";

// This file is the regression signal for the Vercel AI Gateway wiring:
// if a future refactor accidentally makes the test branch talk to the
// real gateway, these tests either stop being deterministic or fail
// with an auth error. Either way the signal is loud.

describe("myProvider (test environment)", () => {
  test("isTestEnvironment is true under vitest", () => {
    // We lean on NODE_ENV=test (vitest sets this) so the mock branch
    // activates. If this ever flips to false, production model code
    // would silently start firing from the unit-test process — bad.
    expect(isTestEnvironment).toBe(true);
  });

  test("chat-model generates canned text without network", async () => {
    const result = await generateText({
      model: myProvider.languageModel("chat-model"),
      prompt: "Hi",
    });
    expect(result.text).toBe("Hello, world!");
    expect(result.finishReason).toBe("stop");
  });

  test("chat-model streams mock chunks", async () => {
    const result = streamText({
      model: myProvider.languageModel("chat-model"),
      prompt: "Hi",
    });

    let collected = "";
    for await (const chunk of result.textStream) {
      collected += chunk;
    }
    // Default getResponseChunksByPrompt returns "Mock response"
    // word-split into deltas of "Mock " and "response ".
    expect(collected.trim()).toBe("Mock response");
  });

  test("title-model returns a short canned title", async () => {
    const result = await generateText({
      model: myProvider.languageModel("title-model"),
      prompt: "Title this",
    });
    expect(result.text).toBe("This is a test title");
  });
});
