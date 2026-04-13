import * as Sentry from "@sentry/node";
import { serve } from "@hono/node-server";
import app from "./app";

// Sentry error tracking (no-op if DSN not set)
const sentryDsn = process.env.SENTRY_DSN;
if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    environment: process.env.APP_ENVIRONMENT || "development",
    tracesSampleRate: 0.1,
  });
}

serve(
  {
    fetch: app.fetch,
    port: 3000,
  },
  (info) => {
    console.log(`Server is running on http://localhost:${info.port}`);
  },
);
