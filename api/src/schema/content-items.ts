import {
  pgTable,
  uuid,
  text,
  integer,
  jsonb,
  timestamp,
} from "drizzle-orm/pg-core";
import { learningDays } from "./learning-days";

export const contentItems = pgTable("content_item", {
  id: uuid("id").notNull().defaultRandom().primaryKey(),
  learningDayId: uuid("learning_day_id").references(() => learningDays.id),
  contentType: text("content_type").notNull(),
  sefer: text("sefer").notNull(),
  perek: integer("perek").notNull(),
  halachaStart: integer("halacha_start"),
  halachaEnd: integer("halacha_end"),
  title: text("title"),
  content: jsonb("content").notNull(),
  imageUrl: text("image_url"),
  thumbnailUrl: text("thumbnail_url"),
  status: text("status").default("draft"),
  reviewedBy: text("reviewed_by").array(),
  reviewNotes: text("review_notes"),
  publishedAt: timestamp("published_at", { withTimezone: true }),
  generationModel: text("generation_model"),
  sortOrder: integer("sort_order").default(0),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
});
