import { pgTable, uuid, text, timestamp } from "drizzle-orm/pg-core";

export const whatsappSubscribers = pgTable("whatsapp_subscriber", {
  id: uuid("id").notNull().defaultRandom().primaryKey(),
  phoneHash: text("phone_hash").unique().notNull(),
  track: text("track").default("3-perek"),
  subscribedAt: timestamp("subscribed_at", { withTimezone: true }).defaultNow(),
  unsubscribedAt: timestamp("unsubscribed_at", { withTimezone: true }),
  status: text("status").default("active"),
});
