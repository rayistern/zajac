import {
  pgTable,
  uuid,
  text,
  integer,
  timestamp,
  uniqueIndex,
} from "drizzle-orm/pg-core";

/**
 * Canonical mapping: Rambam halacha → positive/negative mitzvah reference
 * from Sefer Hamitzvos. Populated from Sefaria index (primary) or a curated
 * CSV fallback (see PHASE_1_5_SCOPE.md open question #1).
 *
 * Display-only in Phase 1.5 — no editorial commentary, no user preferences.
 */
export const seferHamitzvosReference = pgTable(
  "sefer_hamitzvos_reference",
  {
    id: uuid("id").notNull().defaultRandom().primaryKey(),
    rambamRef: text("rambam_ref").notNull(),
    mitzvahType: text("mitzvah_type").notNull(),
    mitzvahNumber: integer("mitzvah_number").notNull(),
    titleHe: text("title_he"),
    titleEn: text("title_en"),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
  },
  (table) => [
    uniqueIndex("sefer_hamitzvos_ref_unique").on(
      table.rambamRef,
      table.mitzvahType,
      table.mitzvahNumber,
    ),
  ],
);
