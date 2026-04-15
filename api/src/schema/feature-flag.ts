import { pgTable, text, jsonb, timestamp } from "drizzle-orm/pg-core";

/**
 * Feature-flag key/value store. Every Phase 1.5 surface is gated by a
 * `phase_1_5_*` flag resolved once per request by the feature-flag
 * middleware; production stays off until launch readiness approves.
 *
 * `value` is jsonb so flags can express richer shapes than booleans
 * (e.g., per-device rollout, variant allocations) without a migration.
 *
 * See docs/PHASE_1_5_SCOPE.md §Shared foundations.
 */
export const featureFlags = pgTable("feature_flag", {
  key: text("key").primaryKey(),
  value: jsonb("value").notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true })
    .notNull()
    .defaultNow(),
});
