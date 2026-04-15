import {
  pgTable,
  uuid,
  text,
  timestamp,
  uniqueIndex,
} from "drizzle-orm/pg-core";
import { contentItems } from "./content-items";

/**
 * Device-scoped bookmarks for content items.
 *
 * Phase 1.5 ships privacy-by-default: no user-entered notes, anonymous
 * device_id only. Composite uniqueness prevents duplicate bookmarks of
 * the same item by the same device.
 *
 * See docs/PHASE_1_5_SCOPE.md §bookmarks.
 */
export const bookmarks = pgTable(
  "bookmark",
  {
    id: uuid("id").notNull().defaultRandom().primaryKey(),
    deviceId: text("device_id").notNull(),
    contentItemId: uuid("content_item_id")
      .notNull()
      .references(() => contentItems.id, { onDelete: "cascade" }),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  },
  (table) => [
    uniqueIndex("bookmark_device_content_unique").on(
      table.deviceId,
      table.contentItemId,
    ),
  ],
);
