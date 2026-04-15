import { z, createRoute } from "@hono/zod-openapi";
import { cors } from "hono/cors";
import { OpenAPIHono } from "@hono/zod-openapi";
import { contentRoutes } from "./routes/content";
import { rambamRoutes } from "./routes/rambam";
import { sichosRoutes } from "./routes/sichos";
import { shareRoutes } from "./routes/share";
import { preferencesRoutes } from "./routes/preferences";
import { webhookRoutes } from "./routes/webhook";
import { flagsRoutes } from "./routes/flags";

const app = (new OpenAPIHono().use("*", cors()) as OpenAPIHono)
  .openapi(
    createRoute({
      method: "get",
      path: "/",
      responses: {
        200: {
          description: "Health check",
          content: { "text/plain": { schema: z.string() } },
        },
      },
    }),
    (c) => c.text("Merkos Rambam API"),
  )
  .route("/api/content", contentRoutes)
  .route("/api/rambam", rambamRoutes)
  .route("/api/sichos", sichosRoutes)
  .route("/api/share", shareRoutes)
  .route("/api/preferences", preferencesRoutes)
  .route("/api/webhook", webhookRoutes)
  .route("/api/flags", flagsRoutes)
  .doc("/doc", {
    openapi: "3.0.0",
    servers: [
      { url: "http://localhost:3000", description: "Local Server" },
    ],
    info: {
      version: "1.0.0",
      title: "Merkos Rambam API",
    },
  });

export default app;
