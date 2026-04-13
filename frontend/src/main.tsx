import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, createRouter } from "@tanstack/react-router";
import * as Sentry from "@sentry/react";
import posthog from "posthog-js";
import { routeTree } from "./routeTree.gen";
import "./styles/index.css";

// PostHog analytics (no-op if key not set)
const posthogKey = import.meta.env.VITE_POSTHOG_KEY;
if (posthogKey) {
  posthog.init(posthogKey, {
    api_host: import.meta.env.VITE_POSTHOG_HOST || "https://us.i.posthog.com",
    autocapture: true,
    capture_pageview: true,
    persistence: "localStorage",
  });
}

// Sentry error tracking (no-op if DSN not set)
const sentryDsn = import.meta.env.VITE_SENTRY_DSN;
if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    environment: import.meta.env.MODE,
    tracesSampleRate: 0.1,
  });
}

const queryClient = new QueryClient();
const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Sentry.ErrorBoundary
      fallback={({ error, resetError }) => (
        <div className="min-h-screen bg-[var(--bg)] text-white flex flex-col items-center justify-center p-8 text-center">
          <h1 className="text-xl font-bold mb-4">Something went wrong</h1>
          <p className="text-[var(--grey)] text-sm mb-6 max-w-sm">
            {error instanceof Error ? error.message : "An unexpected error occurred."}
          </p>
          <button
            onClick={resetError}
            className="px-5 py-2.5 bg-[var(--green)] rounded-xl text-sm font-bold text-[var(--bg)]"
          >
            Try Again
          </button>
        </div>
      )}
    >
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </Sentry.ErrorBoundary>
  </StrictMode>,
);
