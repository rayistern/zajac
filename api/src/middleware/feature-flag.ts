import type { MiddlewareHandler } from "hono";
import { db } from "../db";
import { featureFlags } from "../schema";

/**
 * Phase 1.5 gates every new surface behind a ``phase_1_5_*`` feature flag.
 *
 * Usage:
 *   app.use("/api/bookmarks/*", requireFeatureFlag("phase_1_5_bookmarks"))
 *
 * The middleware reads ``feature_flag.value`` (jsonb) for ``key``:
 *
 *   - ``true``            — allow the request
 *   - ``false``           — reject with 503 + ``{ error: "feature_disabled" }``
 *   - missing row         — reject with 503 (flags default off in production)
 *   - ``{ enabled: bool }`` — long-form shape; ``enabled`` wins
 *
 * Resolving the flag happens once per request and is stashed on the context
 * so downstream handlers can read it via ``c.get("featureFlag")``.
 */
export function requireFeatureFlag(key: string): MiddlewareHandler {
  return async (c, next) => {
    const value = await resolveFlagValue(key);
    if (!isFlagEnabled(value)) {
      return c.json(
        {
          error: "feature_disabled",
          message: `Feature ${key} is currently disabled.`,
        },
        503,
      );
    }
    c.set("featureFlag", { key, value });
    await next();
  };
}

/**
 * Resolve a single flag by key. Returns the raw jsonb value, or ``null``
 * when no row exists. Callers typically feed the result to
 * ``isFlagEnabled``; the ``GET /api/flags`` route returns raw values.
 */
export async function resolveFlagValue(key: string): Promise<unknown | null> {
  const rows = await db
    .select({ value: featureFlags.value })
    .from(featureFlags)
    .where(eqKey(key))
    .limit(1);
  return rows[0]?.value ?? null;
}

/**
 * Fetch all flags in one round-trip (for ``GET /api/flags``).
 *
 * Returns a plain object keyed by flag name. The map shape lets the client
 * bulk-check flags without N round-trips; the feature-flag table is tiny
 * and fully cacheable at the CDN if we ever want to.
 */
export async function fetchAllFlags(): Promise<Record<string, unknown>> {
  const rows = await db
    .select({ key: featureFlags.key, value: featureFlags.value })
    .from(featureFlags);
  const out: Record<string, unknown> = {};
  for (const row of rows) out[row.key] = row.value;
  return out;
}

/**
 * Normalize flag value to a boolean. Accepts the two shapes documented
 * above (bare boolean or ``{ enabled: bool }``).
 */
export function isFlagEnabled(value: unknown): boolean {
  if (value === true) return true;
  if (value === false || value == null) return false;
  if (typeof value === "object" && "enabled" in value) {
    return Boolean((value as { enabled?: unknown }).enabled);
  }
  return false;
}

// --- internal ---

// Inlined eq() so we don't import drizzle-orm here purely for a single op.
// featureFlags.key is a text PK; Drizzle exposes it as a column that works
// with its generic eq helper.
import { eq } from "drizzle-orm";
function eqKey(key: string) {
  return eq(featureFlags.key, key);
}
