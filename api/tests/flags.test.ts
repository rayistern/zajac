import { beforeEach, describe, expect, test } from "vitest";
import { clearAll } from "./helpers";
import { db } from "./setup";
import { testClient } from "hono/testing";
import app from "../src/app";
import {
  isFlagEnabled,
  requireFeatureFlag,
  fetchAllFlags,
} from "../src/middleware/feature-flag";
import { featureFlags } from "../src/schema";
import { OpenAPIHono, createRoute, z } from "@hono/zod-openapi";

describe("Feature flags: GET /api/flags", () => {
  const client = testClient(app);

  beforeEach(async () => {
    await clearAll();
  });

  test("returns empty map when no flags exist", async () => {
    const res = await client.api.flags.$get({ header: {} });
    expect(res.status).toBe(200);
    const data = (await res.json()) as { flags: Record<string, unknown> };
    expect(data.flags).toEqual({});
  });

  test("returns every flag, keyed by name", async () => {
    await db.insert(featureFlags).values([
      { key: "phase_1_5_bookmarks", value: true },
      { key: "phase_1_5_quizzes", value: false },
      { key: "phase_1_5_raise_hand", value: { enabled: true, rollout: 0.25 } },
    ]);

    const res = await client.api.flags.$get({
      header: { "x-device-id": "test-device" },
    });

    expect(res.status).toBe(200);
    const data = (await res.json()) as { flags: Record<string, unknown> };
    expect(data.flags).toEqual({
      phase_1_5_bookmarks: true,
      phase_1_5_quizzes: false,
      phase_1_5_raise_hand: { enabled: true, rollout: 0.25 },
    });
  });
});

describe("Feature flags: isFlagEnabled", () => {
  test("true passes", () => {
    expect(isFlagEnabled(true)).toBe(true);
  });

  test("false rejects", () => {
    expect(isFlagEnabled(false)).toBe(false);
  });

  test("null/missing rejects (flags default off)", () => {
    expect(isFlagEnabled(null)).toBe(false);
    expect(isFlagEnabled(undefined)).toBe(false);
  });

  test("object with enabled: true passes", () => {
    expect(isFlagEnabled({ enabled: true, rollout: 0.5 })).toBe(true);
  });

  test("object with enabled: false rejects", () => {
    expect(isFlagEnabled({ enabled: false })).toBe(false);
  });

  test("object without enabled key rejects", () => {
    expect(isFlagEnabled({ rollout: 0.5 })).toBe(false);
  });

  test("strings, numbers, arrays reject (unknown shape = off)", () => {
    expect(isFlagEnabled("true")).toBe(false);
    expect(isFlagEnabled(1)).toBe(false);
    expect(isFlagEnabled([true])).toBe(false);
  });
});

describe("Feature flags: requireFeatureFlag middleware", () => {
  // Build a tiny local app so the middleware is exercised in isolation.
  // The surface-level routes in the main app aren't gated yet (they land
  // with each feature PR), so this test is the regression signal for the
  // gating behaviour itself.
  function buildTestApp(flagKey: string) {
    const testRoute = createRoute({
      method: "get",
      path: "/",
      responses: {
        200: {
          description: "ok",
          content: {
            "application/json": { schema: z.object({ ok: z.boolean() }) },
          },
        },
        503: {
          description: "disabled",
          content: {
            "application/json": {
              schema: z.object({ error: z.string(), message: z.string() }),
            },
          },
        },
      },
    });
    return new OpenAPIHono()
      .use("*", requireFeatureFlag(flagKey))
      .openapi(testRoute, (c) => c.json({ ok: true }, 200));
  }

  beforeEach(async () => {
    await clearAll();
  });

  test("rejects with 503 when flag row is missing", async () => {
    const testApp = buildTestApp("phase_1_5_bookmarks");
    const res = await testApp.request("/");
    expect(res.status).toBe(503);
    const data = (await res.json()) as { error: string };
    expect(data.error).toBe("feature_disabled");
  });

  test("rejects with 503 when flag is false", async () => {
    await db
      .insert(featureFlags)
      .values({ key: "phase_1_5_bookmarks", value: false });
    const testApp = buildTestApp("phase_1_5_bookmarks");
    const res = await testApp.request("/");
    expect(res.status).toBe(503);
  });

  test("allows when flag is true", async () => {
    await db
      .insert(featureFlags)
      .values({ key: "phase_1_5_bookmarks", value: true });
    const testApp = buildTestApp("phase_1_5_bookmarks");
    const res = await testApp.request("/");
    expect(res.status).toBe(200);
    const data = (await res.json()) as { ok: boolean };
    expect(data.ok).toBe(true);
  });

  test("allows when flag is { enabled: true }", async () => {
    await db
      .insert(featureFlags)
      .values({ key: "phase_1_5_raise_hand", value: { enabled: true } });
    const testApp = buildTestApp("phase_1_5_raise_hand");
    const res = await testApp.request("/");
    expect(res.status).toBe(200);
  });
});

describe("Feature flags: fetchAllFlags helper", () => {
  beforeEach(async () => {
    await clearAll();
  });

  test("returns empty object when no rows", async () => {
    expect(await fetchAllFlags()).toEqual({});
  });

  test("round-trips jsonb values including nested shapes", async () => {
    await db.insert(featureFlags).values([
      { key: "a", value: true },
      { key: "b", value: { enabled: false, variant: "control" } },
      { key: "c", value: [1, 2, 3] },
    ]);
    const flags = await fetchAllFlags();
    expect(flags).toEqual({
      a: true,
      b: { enabled: false, variant: "control" },
      c: [1, 2, 3],
    });
  });
});
