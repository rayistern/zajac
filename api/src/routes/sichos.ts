import { z, createRoute } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { db } from "../db";
import { sichosReferences } from "../schema";
import { eq, and } from "drizzle-orm";

const sichosRefSchema = z.object({
  id: z.string(),
  halacha: z.number(),
  sourceVolume: z.string(),
  sourcePage: z.string().nullable(),
  sourceUrl: z.string().nullable(),
  excerpt: z.string().nullable(),
  excerptHe: z.string().nullable(),
});

const perekSichosRoute = createRoute({
  method: "get",
  path: "/{sefer}/{perek}",
  request: {
    params: z.object({
      sefer: z.string(),
      perek: z.coerce.number().int().positive(),
    }),
  },
  responses: {
    200: {
      description: "Sichos references for a perek",
      content: {
        "application/json": { schema: z.array(sichosRefSchema) },
      },
    },
  },
});

export const sichosRoutes = new OpenAPIHono().openapi(
  perekSichosRoute,
  async (c) => {
    const { sefer, perek } = c.req.valid("param");
    const refs = await db
      .select()
      .from(sichosReferences)
      .where(
        and(eq(sichosReferences.sefer, sefer), eq(sichosReferences.perek, perek)),
      );

    return c.json(
      refs.map((r) => ({
        id: r.id,
        halacha: r.halacha,
        sourceVolume: r.sourceVolume,
        sourcePage: r.sourcePage,
        sourceUrl: r.sourceUrl,
        excerpt: r.excerpt,
        excerptHe: r.excerptHe,
      })),
      200,
    );
  },
);
