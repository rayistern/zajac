import { z, createRoute } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { db } from "../db";
import { contentItems } from "../schema";
import { eq } from "drizzle-orm";

const metaRoute = createRoute({
  method: "get",
  path: "/{contentId}/meta",
  request: {
    params: z.object({ contentId: z.string().uuid() }),
  },
  responses: {
    200: {
      description: "HTML page with OG meta tags for social sharing",
      content: { "text/html": { schema: z.string() } },
    },
    404: { description: "Content not found" },
  },
});

export const shareRoutes = new OpenAPIHono().openapi(metaRoute, async (c) => {
  const { contentId } = c.req.valid("param");

  const item = await db
    .select()
    .from(contentItems)
    .where(eq(contentItems.id, contentId))
    .limit(1);

  if (!item.length) return c.text("Not found", 404);

  const i = item[0];
  const title = i.title ?? `Rambam — ${i.sefer} ${i.perek}`;
  const description = `Daily Rambam learning: ${i.contentType.replace(/_/g, " ")}`;
  const imageUrl = i.imageUrl ?? "";
  const appUrl = c.req.url.replace(/\/api\/share\/.*/, "");

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta property="og:title" content="${escapeHtml(title)}">
  <meta property="og:description" content="${escapeHtml(description)}">
  <meta property="og:image" content="${escapeHtml(imageUrl)}">
  <meta property="og:url" content="${escapeHtml(appUrl)}">
  <meta property="og:type" content="article">
  <meta name="twitter:card" content="summary_large_image">
  <title>${escapeHtml(title)}</title>
  <meta http-equiv="refresh" content="0;url=${escapeHtml(appUrl)}">
</head>
<body>
  <p>Redirecting to Merkos Rambam...</p>
</body>
</html>`;

  return c.html(html);
});

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
