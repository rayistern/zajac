import { beforeEach, describe, expect, test } from "vitest";
import { clearAll } from "./helpers";
import { learningDays, contentItems } from "../src/schema";
import { db } from "./setup";
import { eq } from "drizzle-orm";

describe("Content queries", () => {
  beforeEach(async () => {
    await clearAll();
  });

  test("can insert and query learning days", async () => {
    await db.insert(learningDays).values({
      date: "2026-04-05",
      hebrewDate: "5 Nissan 5786",
      track1Perakim: [{ sefer: "Beis HaBechirah", perek: 1 }],
      track3Perakim: [
        { sefer: "Beis HaBechirah", perek: 1 },
        { sefer: "Beis HaBechirah", perek: 2 },
        { sefer: "Beis HaBechirah", perek: 3 },
      ],
    });

    const days = await db.select().from(learningDays);
    expect(days).lengthOf(1);
    expect(days[0].date).toBe("2026-04-05");
    expect(days[0].hebrewDate).toBe("5 Nissan 5786");
  });

  test("can insert and query content items", async () => {
    const [day] = await db
      .insert(learningDays)
      .values({
        date: "2026-04-05",
        hebrewDate: "5 Nissan 5786",
        track1Perakim: [],
        track3Perakim: [],
      })
      .returning();

    await db.insert(contentItems).values({
      learningDayId: day.id,
      contentType: "perek_overview",
      sefer: "Beis HaBechirah",
      perek: 1,
      title: "Overview of Perek 1",
      content: { text: "The commandment to build the Temple." },
      status: "published",
    });

    const items = await db
      .select()
      .from(contentItems)
      .where(eq(contentItems.learningDayId, day.id));
    expect(items).lengthOf(1);
    expect(items[0].contentType).toBe("perek_overview");
  });
});
