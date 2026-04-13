import { pgTable, uuid, text, timestamp } from "drizzle-orm/pg-core";
import { contentItems } from "./content-items";

export const shareEvents = pgTable("share_event", {
  id: uuid("id").notNull().defaultRandom().primaryKey(),
  contentItemId: uuid("content_item_id").references(() => contentItems.id),
  platform: text("platform"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});
