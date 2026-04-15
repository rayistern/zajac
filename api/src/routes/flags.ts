import { z, createRoute } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { fetchAllFlags } from "../middleware/feature-flag";

const flagsSchema = z.object({
  flags: z.record(z.string(), z.unknown()),
});

const getFlagsRoute = createRoute({
  method: "get",
  path: "/",
  request: {
    headers: z.object({ "x-device-id": z.string().optional() }),
  },
  responses: {
    200: {
      description:
        "All feature flags, keyed by flag name. Values are the raw jsonb blobs — clients should treat booleans as the happy path and ignore shapes they don't recognise.",
      content: { "application/json": { schema: flagsSchema } },
    },
  },
});

export const flagsRoutes = new OpenAPIHono().openapi(
  getFlagsRoute,
  async (c) => {
    // Device ID is accepted as a header so we can later bucket flags per
    // device (e.g., staged rollout) without a breaking contract change.
    // For Phase 1.5 every flag is global so the header is currently unused.
    const flags = await fetchAllFlags();
    return c.json({ flags }, 200);
  },
);
