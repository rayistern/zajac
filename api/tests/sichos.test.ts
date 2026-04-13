import { beforeEach, describe, expect, test } from "vitest";
import { clearAll } from "./helpers";
import { testClient } from "hono/testing";
import app from "../src/app";
import { db } from "./setup";
import { sichosReferences } from "../src/schema";

describe("Sichos routes", () => {
  const client = testClient(app);

  beforeEach(async () => {
    await clearAll();
  });

  describe("GET /api/sichos/:sefer/:perek", () => {
    test("returns sichos references for a perek", async () => {
      await db.insert(sichosReferences).values([
        {
          sefer: "Shabbat",
          perek: 1,
          halacha: 1,
          sourceVolume: "Likkutei Sichos Vol. 16",
          sourcePage: "p. 234",
          excerpt: "The concept of Shabbat boundaries",
          excerptHe: "גדר שביתה בשבת",
        },
        {
          sefer: "Shabbat",
          perek: 1,
          halacha: 3,
          sourceVolume: "Likkutei Sichos Vol. 16",
          sourcePage: "p. 240",
          excerpt: "The deeper meaning of rest",
        },
      ]);

      const res = await client.api.sichos[":sefer"][":perek"].$get({
        param: { sefer: "Shabbat", perek: 1 },
      });

      expect(res.status).toBe(200);
      const data = (await res.json()) as any;
      expect(data).toHaveLength(2);
      expect(data[0].sourceVolume).toBe("Likkutei Sichos Vol. 16");
      expect(data[0].halacha).toBe(1);
      expect(data[1].halacha).toBe(3);
    });

    test("returns empty array for perek with no sichos", async () => {
      const res = await client.api.sichos[":sefer"][":perek"].$get({
        param: { sefer: "NonExistent", perek: 99 },
      });

      expect(res.status).toBe(200);
      const data = (await res.json()) as any;
      expect(data).toHaveLength(0);
    });
  });
});
