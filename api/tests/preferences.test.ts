import { beforeEach, describe, expect, test } from "vitest";
import { clearAll } from "./helpers";
import { testClient } from "hono/testing";
import app from "../src/app";

describe("Preferences routes", () => {
  const client = testClient(app);

  beforeEach(async () => {
    await clearAll();
  });

  describe("GET /api/preferences", () => {
    test("returns default track when no device id", async () => {
      const res = await client.api.preferences.$get({
        header: {},
      });

      expect(res.status).toBe(200);
      const data = (await res.json()) as any;
      expect(data.track).toBe("3-perek");
    });

    test("returns default track for unknown device", async () => {
      const res = await client.api.preferences.$get({
        header: { "x-device-id": "unknown-device-123" },
      });

      expect(res.status).toBe(200);
      const data = (await res.json()) as any;
      expect(data.track).toBe("3-perek");
    });
  });

  describe("PUT /api/preferences", () => {
    test("creates preference and retrieves it", async () => {
      const deviceId = "test-device-001";

      // Set preference
      const putRes = await client.api.preferences.$put({
        header: { "x-device-id": deviceId },
        json: { track: "1-perek" },
      });

      expect(putRes.status).toBe(200);
      const putData = (await putRes.json()) as any;
      expect(putData.track).toBe("1-perek");

      // Read it back
      const getRes = await client.api.preferences.$get({
        header: { "x-device-id": deviceId },
      });

      expect(getRes.status).toBe(200);
      const getData = (await getRes.json()) as any;
      expect(getData.track).toBe("1-perek");
    });

    test("updates existing preference", async () => {
      const deviceId = "test-device-002";

      await client.api.preferences.$put({
        header: { "x-device-id": deviceId },
        json: { track: "1-perek" },
      });

      const putRes = await client.api.preferences.$put({
        header: { "x-device-id": deviceId },
        json: { track: "3-perek" },
      });

      expect(putRes.status).toBe(200);
      const data = (await putRes.json()) as any;
      expect(data.track).toBe("3-perek");
    });
  });
});
