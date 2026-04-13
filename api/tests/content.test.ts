import { beforeEach, describe, expect, test } from "vitest";
import { clearAll } from "./helpers";
import { testClient } from "hono/testing";
import app from "../src/app";
import { db } from "./setup";
import { learningDays, contentItems } from "../src/schema";

describe("Content routes", () => {
  const client = testClient(app);

  beforeEach(async () => {
    await clearAll();
  });

  async function seedDay(date: string) {
    const [day] = await db
      .insert(learningDays)
      .values({
        date,
        hebrewDate: "5 Nissan 5786",
        track1Perakim: [{ sefer: "Shabbat", perek: 1 }],
        track3Perakim: [
          { sefer: "Shabbat", perek: 1 },
          { sefer: "Shabbat", perek: 2 },
          { sefer: "Shabbat", perek: 3 },
        ],
      })
      .returning();
    return day;
  }

  async function seedItem(dayId: string, overrides: Partial<typeof contentItems.$inferInsert> = {}) {
    const [item] = await db
      .insert(contentItems)
      .values({
        learningDayId: dayId,
        contentType: "perek_overview",
        sefer: "Shabbat",
        perek: 1,
        title: "Overview",
        content: { text: "Test content" },
        status: "published",
        ...overrides,
      })
      .returning();
    return item;
  }

  describe("GET /api/content/day/:date", () => {
    test("returns content for a date with published items", async () => {
      const day = await seedDay("2026-04-05");
      await seedItem(day.id);
      await seedItem(day.id, {
        contentType: "conceptual_image",
        title: "Image",
        content: { caption: "A test image" },
        imageUrl: "https://example.com/img.webp",
      });

      const res = await client.api.content.day[":date"].$get({
        param: { date: "2026-04-05" },
        query: { track: "3-perek" },
      });

      expect(res.status).toBe(200);
      const data = (await res.json()) as any;
      expect(data.date).toBe("2026-04-05");
      expect(data.hebrewDate).toBe("5 Nissan 5786");
      expect(data.items).toHaveLength(2);
      expect(data.perakim).toHaveLength(3);
    });

    test("returns 1-perek track when specified", async () => {
      const day = await seedDay("2026-04-06");
      await seedItem(day.id);

      const res = await client.api.content.day[":date"].$get({
        param: { date: "2026-04-06" },
        query: { track: "1-perek" },
      });

      expect(res.status).toBe(200);
      const data = (await res.json()) as any;
      expect(data.perakim).toHaveLength(1);
    });

    test("returns 404 for non-existent date", async () => {
      const res = await client.api.content.day[":date"].$get({
        param: { date: "2099-01-01" },
        query: { track: "3-perek" },
      });

      expect(res.status).toBe(404);
    });

    test("excludes draft items", async () => {
      const day = await seedDay("2026-04-07");
      await seedItem(day.id, { status: "draft" });
      await seedItem(day.id, { status: "published", title: "Published" });

      const res = await client.api.content.day[":date"].$get({
        param: { date: "2026-04-07" },
        query: { track: "3-perek" },
      });

      expect(res.status).toBe(200);
      const data = (await res.json()) as any;
      expect(data.items).toHaveLength(1);
      expect(data.items[0].title).toBe("Published");
    });
  });

  describe("GET /api/content/item/:id", () => {
    test("returns a single content item by id", async () => {
      const day = await seedDay("2026-04-08");
      const item = await seedItem(day.id, { title: "Specific Item" });

      const res = await client.api.content.item[":id"].$get({
        param: { id: item.id },
      });

      expect(res.status).toBe(200);
      const data = (await res.json()) as any;
      expect(data.id).toBe(item.id);
      expect(data.title).toBe("Specific Item");
      expect(data.contentType).toBe("perek_overview");
    });

    test("returns 404 for non-existent item", async () => {
      const res = await client.api.content.item[":id"].$get({
        param: { id: "00000000-0000-0000-0000-000000000000" },
      });

      expect(res.status).toBe(404);
    });
  });
});
