import { z, createRoute } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { db } from "../db";
import { userPreferences } from "../schema";
import { eq } from "drizzle-orm";

const prefsSchema = z.object({
  track: z.enum(["1-perek", "3-perek"]),
});

const getRoute = createRoute({
  method: "get",
  path: "/",
  request: {
    headers: z.object({ "x-device-id": z.string().optional() }),
  },
  responses: {
    200: {
      description: "User preferences",
      content: { "application/json": { schema: prefsSchema } },
    },
  },
});

const putRoute = createRoute({
  method: "put",
  path: "/",
  request: {
    headers: z.object({ "x-device-id": z.string() }),
    body: {
      content: { "application/json": { schema: prefsSchema } },
    },
  },
  responses: {
    200: {
      description: "Updated preferences",
      content: { "application/json": { schema: prefsSchema } },
    },
  },
});

export const preferencesRoutes = new OpenAPIHono()
  .openapi(getRoute, async (c) => {
    const deviceId = c.req.header("x-device-id");
    if (!deviceId) return c.json({ track: "3-perek" as const }, 200);

    const prefs = await db
      .select()
      .from(userPreferences)
      .where(eq(userPreferences.deviceId, deviceId))
      .limit(1);

    return c.json(
      { track: (prefs[0]?.track ?? "3-perek") as "1-perek" | "3-perek" },
      200,
    );
  })
  .openapi(putRoute, async (c) => {
    const deviceId = c.req.header("x-device-id")!;
    const { track } = c.req.valid("json");

    await db
      .insert(userPreferences)
      .values({ deviceId, track })
      .onConflictDoUpdate({
        target: userPreferences.deviceId,
        set: { track, updatedAt: new Date() },
      });

    return c.json({ track }, 200);
  });
