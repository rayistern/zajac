import { pgTable, uuid, text, integer, timestamp } from "drizzle-orm/pg-core";

export const sichosReferences = pgTable("sichos_reference", {
  id: uuid("id").notNull().defaultRandom().primaryKey(),
  sefer: text("sefer").notNull(),
  perek: integer("perek").notNull(),
  halacha: integer("halacha").notNull(),
  sourceVolume: text("source_volume").notNull(),
  sourcePage: text("source_page"),
  sourceUrl: text("source_url"),
  excerpt: text("excerpt"),
  excerptHe: text("excerpt_he"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});
