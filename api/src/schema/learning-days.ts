import { pgTable, uuid, date, text, jsonb, timestamp } from "drizzle-orm/pg-core";

export const learningDays = pgTable("learning_day", {
  id: uuid("id").notNull().defaultRandom().primaryKey(),
  date: date("date").notNull().unique(),
  hebrewDate: text("hebrew_date"),
  track1Perakim: jsonb("track_1_perakim").notNull(),
  track3Perakim: jsonb("track_3_perakim").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});
