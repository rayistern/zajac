import { beforeEach, describe, expect, test } from "vitest";
import { clearAll } from "./helpers";
import { testClient } from "hono/testing";
import app from "../src/app";

describe("API Health", () => {
  const client = testClient(app);
  beforeEach(async () => {
    await clearAll();
  });

  test("health check returns API name", async () => {
    const res = await client.index.$get();
    expect(res.status).toBe(200);
    expect(await res.text()).toBe("Merkos Rambam API");
  });
});
