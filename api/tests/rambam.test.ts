import { beforeEach, describe, expect, test, vi, afterEach } from "vitest";
import "./setup";
import { testClient } from "hono/testing";
import app from "../src/app";

describe("Rambam routes (Sefaria proxy)", () => {
  const client = testClient(app);
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  describe("GET /api/rambam/:sefer/:perek", () => {
    test("returns halachot from Sefaria", async () => {
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({
          versions: [
            { language: "he", text: ["הלכה ראשונה", "הלכה שנייה"] },
            { language: "en", text: ["First halacha", "Second halacha"] },
          ],
        }),
      });

      const res = await client.api.rambam[":sefer"][":perek"].$get({
        param: { sefer: "shabbat", perek: 1 },
      });

      expect(res.status).toBe(200);
      const data = (await res.json()) as any;
      expect(data.sefer).toBe("shabbat");
      expect(data.perek).toBe(1);
      expect(data.halachot).toHaveLength(2);
      expect(data.halachot[0].he).toBe("הלכה ראשונה");
      expect(data.halachot[0].en).toBe("First halacha");
    });

    test("returns 502 on Sefaria error", async () => {
      (global.fetch as any).mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({}),
      });

      const res = await client.api.rambam[":sefer"][":perek"].$get({
        param: { sefer: "shabbat", perek: 99 },
      });

      expect(res.status).toBe(502);
    });

    test("handles missing versions gracefully", async () => {
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({ versions: [] }),
      });

      const res = await client.api.rambam[":sefer"][":perek"].$get({
        param: { sefer: "shabbat", perek: 1 },
      });

      expect(res.status).toBe(200);
      const data = (await res.json()) as any;
      expect(data.halachot).toHaveLength(0);
    });
  });

  describe("GET /api/rambam/:sefer/:perek/:halacha", () => {
    test("returns a single halacha", async () => {
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({
          versions: [
            { language: "he", text: "טקסט עברי" },
            { language: "en", text: "English text" },
          ],
        }),
      });

      const res = await client.api.rambam[":sefer"][":perek"][":halacha"].$get({
        param: { sefer: "shabbat", perek: 1, halacha: 3 },
      });

      expect(res.status).toBe(200);
      const data = (await res.json()) as any;
      expect(data.number).toBe(3);
      expect(data.he).toBe("טקסט עברי");
      expect(data.en).toBe("English text");
    });

    test("returns 404 when Hebrew text is missing", async () => {
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({
          versions: [{ language: "en", text: "Only English" }],
        }),
      });

      const res = await client.api.rambam[":sefer"][":perek"][":halacha"].$get({
        param: { sefer: "shabbat", perek: 1, halacha: 3 },
      });

      expect(res.status).toBe(404);
    });

    test("returns 502 on Sefaria error", async () => {
      (global.fetch as any).mockRejectedValue(new Error("Network error"));

      const res = await client.api.rambam[":sefer"][":perek"][":halacha"].$get({
        param: { sefer: "shabbat", perek: 1, halacha: 3 },
      });

      expect(res.status).toBe(502);
    });
  });
});
