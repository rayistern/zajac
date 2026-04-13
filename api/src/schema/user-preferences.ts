import { pgTable, uuid, text, timestamp } from "drizzle-orm/pg-core";

export const userPreferences = pgTable("user_preference", {
  id: uuid("id").notNull().defaultRandom().primaryKey(),
  deviceId: text("device_id").unique(),
  track: text("track").default("3-perek"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
});
