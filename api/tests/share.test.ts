import { beforeEach, describe, expect, test } from "vitest";
import { clearAll } from "./helpers";
import { testClient } from "hono/testing";
import app from "../src/app";
import { db } from "./setup";
import { learningDays, contentItems } from "../src/schema";

describe("Share routes", () => {
  const client = testClient(app);

  beforeEach(async () => {
    await clearAll();
  });

  describe("GET /api/share/:contentId/meta", () => {
    test("returns HTML with OG meta tags", async () => {
      const [day] = await db
        .insert(learningDays)
        .values({
          date: "2026-04-10",
          hebrewDate: "10 Nissan 5786",
          track1Perakim: [],
          track3Perakim: [],
        })
        .returning();

      const [item] = await db
        .insert(contentItems)
        .values({
          learningDayId: day.id,
          contentType: "conceptual_image",
          sefer: "Shabbat",
          perek: 1,
          title: "Shabbat Boundaries",
          content: { caption: "Visual representation" },
          imageUrl: "https://example.com/image.webp",
          status: "published",
        })
        .returning();

      const res = await client.api.share[":contentId"].meta.$get({
        param: { contentId: item.id },
      });

      expect(res.status).toBe(200);
      const html = await res.text();
      expect(html).toContain("og:title");
      expect(html).toContain("Shabbat Boundaries");
      expect(html).toContain("og:image");
      expect(html).toContain("https://example.com/image.webp");
      expect(html).toContain("twitter:card");
    });

    test("returns 404 for non-existent content", async () => {
      const res = await client.api.share[":contentId"].meta.$get({
        param: { contentId: "00000000-0000-0000-0000-000000000000" },
      });

      expect(res.status).toBe(404);
    });
  });
});
