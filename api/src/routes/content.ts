import { z, createRoute } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { db } from "../db";
import { learningDays, contentItems } from "../schema";
import { eq, and, sql } from "drizzle-orm";

const trackParam = z.enum(["1-perek", "3-perek"]).default("3-perek");

const contentItemSchema = z.object({
  id: z.string(),
  contentType: z.string(),
  sefer: z.string(),
  perek: z.number(),
  halachaStart: z.number().nullable(),
  halachaEnd: z.number().nullable(),
  title: z.string().nullable(),
  content: z.any(),
  imageUrl: z.string().nullable(),
  thumbnailUrl: z.string().nullable(),
  sortOrder: z.number().nullable(),
});

const dayContentSchema = z.object({
  date: z.string(),
  hebrewDate: z.string().nullable(),
  perakim: z.any(),
  items: z.array(contentItemSchema),
});

const todayRoute = createRoute({
  method: "get",
  path: "/today",
  request: {
    query: z.object({ track: trackParam }),
  },
  responses: {
    200: {
      description: "Today's published content",
      content: { "application/json": { schema: dayContentSchema } },
    },
    404: { description: "No content for today" },
  },
});

const dayRoute = createRoute({
  method: "get",
  path: "/day/{date}",
  request: {
    params: z.object({ date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/) }),
    query: z.object({ track: trackParam }),
  },
  responses: {
    200: {
      description: "Content for a specific date",
      content: { "application/json": { schema: dayContentSchema } },
    },
    404: { description: "No content for this date" },
  },
});

const itemRoute = createRoute({
  method: "get",
  path: "/item/{id}",
  request: {
    params: z.object({ id: z.string().uuid() }),
  },
  responses: {
    200: {
      description: "Single content item",
      content: { "application/json": { schema: contentItemSchema } },
    },
    404: { description: "Content item not found" },
  },
});

async function fetchDayContent(dateStr: string, track: string) {
  const day = await db
    .select()
    .from(learningDays)
    .where(eq(learningDays.date, dateStr))
    .limit(1);

  if (!day.length) return null;

  const items = await db
    .select()
    .from(contentItems)
    .where(
      and(
        eq(contentItems.learningDayId, day[0].id),
        eq(contentItems.status, "published"),
      ),
    )
    .orderBy(contentItems.sortOrder);

  return {
    date: day[0].date,
    hebrewDate: day[0].hebrewDate,
    perakim: track === "1-perek" ? day[0].track1Perakim : day[0].track3Perakim,
    items: items.map((i) => ({
      id: i.id,
      contentType: i.contentType,
      sefer: i.sefer,
      perek: i.perek,
      halachaStart: i.halachaStart,
      halachaEnd: i.halachaEnd,
      title: i.title,
      content: i.content,
      imageUrl: i.imageUrl,
      thumbnailUrl: i.thumbnailUrl,
      sortOrder: i.sortOrder,
    })),
  };
}

function todayDateStr() {
  return new Date().toISOString().split("T")[0];
}

export const contentRoutes = new OpenAPIHono()
  .openapi(todayRoute, async (c) => {
    const { track } = c.req.valid("query");
    const result = await fetchDayContent(todayDateStr(), track);
    if (!result) return c.json({ error: "No content for today" }, 404);
    return c.json(result, 200);
  })
  .openapi(dayRoute, async (c) => {
    const { date } = c.req.valid("param");
    const { track } = c.req.valid("query");
    const result = await fetchDayContent(date, track);
    if (!result) return c.json({ error: "No content for this date" }, 404);
    return c.json(result, 200);
  })
  .openapi(itemRoute, async (c) => {
    const { id } = c.req.valid("param");
    const item = await db
      .select()
      .from(contentItems)
      .where(eq(contentItems.id, id))
      .limit(1);

    if (!item.length) return c.json({ error: "Not found" }, 404);
    const i = item[0];
    return c.json(
      {
        id: i.id,
        contentType: i.contentType,
        sefer: i.sefer,
        perek: i.perek,
        halachaStart: i.halachaStart,
        halachaEnd: i.halachaEnd,
        title: i.title,
        content: i.content,
        imageUrl: i.imageUrl,
        thumbnailUrl: i.thumbnailUrl,
        sortOrder: i.sortOrder,
      },
      200,
    );
  });
