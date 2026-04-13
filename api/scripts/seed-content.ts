/**
 * Seed script — populates the database with sample content for Hilchos Beis HaBechirah.
 *
 * Usage: npx tsx scripts/seed-content.ts
 * Requires: DB_HOST, DB_NAME, DB_USER, DB_PASS env vars (or --env-file=.env.dev)
 */
import { drizzle } from "drizzle-orm/node-postgres";
import { Pool } from "pg";
import { learningDays, contentItems, sichosReferences } from "../src/schema";

const pool = new Pool({
  host: process.env.DB_HOST ?? "localhost:5432",
  database: process.env.DB_NAME ?? "app",
  user: process.env.DB_USER ?? "postgres",
  password: process.env.DB_PASS ?? "postgres",
});

const db = drizzle({ client: pool });

async function seed() {
  console.log("Seeding database...");

  // --- Day 1: Beis HaBechirah Perakim 1-3 ---
  const [day1] = await db
    .insert(learningDays)
    .values({
      date: "2026-04-05",
      hebrewDate: "5 Nissan 5786",
      track1Perakim: [{ sefer: "Beis HaBechirah", perek: 1 }],
      track3Perakim: [
        { sefer: "Beis HaBechirah", perek: 1 },
        { sefer: "Beis HaBechirah", perek: 2 },
        { sefer: "Beis HaBechirah", perek: 3 },
      ],
    })
    .returning();

  await db.insert(contentItems).values([
    {
      learningDayId: day1.id,
      contentType: "perek_overview",
      sefer: "Beis HaBechirah",
      perek: 1,
      title: "The Commandment to Build",
      content: {
        text: "Perek 1 establishes the positive commandment to construct a House for God. It traces the journey of the Sanctuary from the portable Mishkan of the wilderness through Gilgal (14 years), Shiloh (369 years), Nov and Givon (57 years combined), until the eternal structure in Jerusalem on Mount Moriah. Once the Temple was built in Jerusalem, all other locations became permanently forbidden for sacrificial worship.",
      },
      status: "published",
      sortOrder: 0,
    },
    {
      learningDayId: day1.id,
      contentType: "conceptual_image",
      sefer: "Beis HaBechirah",
      perek: 1,
      halachaStart: 5,
      halachaEnd: 5,
      title: "Structure of the Mikdash",
      content: {
        caption:
          "The essential structure: Sanctuary (Kodesh), Holy of Holies (Kodesh HaKodashim), Entrance Hall (Ulam), and the surrounding Courtyard (Azarah).",
        altText:
          "Architectural diagram showing the nested zones of holiness in the Temple complex",
      },
      imageUrl: "https://placehold.co/800x500/1a2020/1DB954?text=Mikdash+Structure",
      thumbnailUrl: "https://placehold.co/400x250/1a2020/1DB954?text=Mikdash",
      status: "published",
      sortOrder: 1,
    },
    {
      learningDayId: day1.id,
      contentType: "infographic",
      sefer: "Beis HaBechirah",
      perek: 1,
      halachaStart: 2,
      halachaEnd: 2,
      title: "From the Desert to the Eternal City",
      content: {
        caption:
          "The journey of the Sanctuary across five locations: Gilgal → Shiloh → Nov → Givon → Jerusalem",
        steps: [
          {
            location: "Gilgal",
            years: 14,
            detail: "Portable Mishkan during conquest and division of the Land",
          },
          {
            location: "Shiloh",
            years: 369,
            detail:
              "Stone walls with Mishkan curtains, no roof. Destroyed when Eli died.",
          },
          {
            location: "Nov",
            years: null,
            detail: "Temporary sanctuary. Destroyed when Shmuel died.",
          },
          {
            location: "Givon",
            years: null,
            detail: "Last stop before the eternal structure.",
          },
          {
            location: "Jerusalem",
            years: "Eternal",
            detail:
              '"This is My resting place forever" — once built, all other locations forbidden.',
          },
        ],
      },
      imageUrl: "https://placehold.co/800x500/111820/64B5F6?text=Sanctuary+Journey",
      thumbnailUrl: "https://placehold.co/400x250/111820/64B5F6?text=Journey",
      status: "published",
      sortOrder: 2,
    },
    {
      learningDayId: day1.id,
      contentType: "did_you_know",
      sefer: "Beis HaBechirah",
      perek: 2,
      title: "Did You Know?",
      content: {
        text: "No iron tools were permitted for the Altar's stones — iron shortens life (war), while the Altar prolongs life (atonement). Even the ramp to the altar had to be built without steps, so the priests wouldn't take wide strides in a disrespectful manner.",
      },
      status: "published",
      sortOrder: 3,
    },
    {
      learningDayId: day1.id,
      contentType: "conceptual_image",
      sefer: "Beis HaBechirah",
      perek: 1,
      halachaStart: 6,
      halachaEnd: 6,
      title: "Seven Sacred Vessels",
      content: {
        caption:
          "The Sanctuary requires seven essential utensils: the main altar, the ramp, the wash basin, the incense altar, the Menorah, the showbread table, and the surrounding curtain partition.",
        altText: "Infographic showing the seven essential vessels of the Mikdash",
      },
      imageUrl: "https://placehold.co/800x500/10160e/B39DDB?text=Seven+Vessels",
      thumbnailUrl: "https://placehold.co/400x250/10160e/B39DDB?text=Vessels",
      status: "published",
      sortOrder: 4,
    },
    {
      learningDayId: day1.id,
      contentType: "perek_overview",
      sefer: "Beis HaBechirah",
      perek: 2,
      title: "The Altar — Dimensions and Laws",
      content: {
        text: "Perek 2 details the construction of the Altar: its exact dimensions, the requirement for a ramp rather than steps, the prohibition of iron tools, and the types of stones that are disqualified. The Altar's location on Mount Moriah is identified as the exact spot where Avraham bound Yitzchak and where Noach and Adam offered their sacrifices.",
      },
      status: "published",
      sortOrder: 5,
    },
    {
      learningDayId: day1.id,
      contentType: "perek_overview",
      sefer: "Beis HaBechirah",
      perek: 3,
      title: "The Wash Basin and the Chambers",
      content: {
        text: "Perek 3 describes the wash basin (kiyor) and its pedestal, the Entrance Hall (Ulam), and the various chambers built around the Temple. It details the ascending levels of holiness from the outer courtyard inward, each marked by physical barriers and specific permissions for who may enter.",
      },
      status: "published",
      sortOrder: 6,
    },
    {
      learningDayId: day1.id,
      contentType: "daily_chart",
      sefer: "Beis HaBechirah",
      perek: 1,
      title: "Timeline of the Sanctuary",
      content: {
        caption:
          "The three eras of the Sanctuary: the portable Mishkan (~480 years), the First Temple (410 years), and the Second Temple (420 years).",
        chartType: "timeline",
      },
      imageUrl: "https://placehold.co/800x400/0d1117/1D9E75?text=Temple+Timeline",
      thumbnailUrl: "https://placehold.co/400x200/0d1117/1D9E75?text=Timeline",
      status: "published",
      sortOrder: 7,
    },
  ]);

  // --- Sichos References ---
  await db.insert(sichosReferences).values([
    {
      sefer: "Beis HaBechirah",
      perek: 1,
      halacha: 1,
      sourceVolume: "Likkutei Sichos Vol. 29",
      sourcePage: "p. 71",
      excerpt:
        "The Mishkan was portable — its sanctity came from its components, not the ground it stood on. The Beis HaMikdash is the opposite: the place itself is holy, even without the building. That's why the Temple required ascending steps between each level of holiness — the spiritual gradations had to be expressed in the physical space.",
      excerptHe: "לקוטי שיחות חכ״ט ע׳ 71",
    },
    {
      sefer: "Beis HaBechirah",
      perek: 3,
      halacha: 1,
      sourceVolume: "Likkutei Sichos Vol. 21",
      sourcePage: "p. 155",
      excerpt:
        "The ascending levels of holiness in the Temple teach that spiritual growth must be embodied in concrete, tangible action. Each physical step upward mirrors an internal ascent. The architecture of the Mikdash is a map of the soul's journey toward the Divine.",
      excerptHe: "לקוטי שיחות חכ״א ע׳ 155",
    },
  ]);

  // --- Day 2: Beis HaBechirah Perakim 4-6 ---
  const [day2] = await db
    .insert(learningDays)
    .values({
      date: "2026-04-06",
      hebrewDate: "6 Nissan 5786",
      track1Perakim: [{ sefer: "Beis HaBechirah", perek: 2 }],
      track3Perakim: [
        { sefer: "Beis HaBechirah", perek: 4 },
        { sefer: "Beis HaBechirah", perek: 5 },
        { sefer: "Beis HaBechirah", perek: 6 },
      ],
    })
    .returning();

  await db.insert(contentItems).values([
    {
      learningDayId: day2.id,
      contentType: "perek_overview",
      sefer: "Beis HaBechirah",
      perek: 4,
      title: "The Courtyard — Dimensions and Divisions",
      content: {
        text: "Perek 4 establishes the dimensions and layout of the Temple courtyard (Azarah). It describes the division into the Court of the Israelites, the Court of the Women, and the surrounding areas. Each zone has specific holiness levels and corresponding restrictions on who may enter.",
      },
      status: "published",
      sortOrder: 0,
    },
    {
      learningDayId: day2.id,
      contentType: "did_you_know",
      sefer: "Beis HaBechirah",
      perek: 5,
      title: "Did You Know?",
      content: {
        text: "The Temple Mount had five gates. The Shushan Gate on the eastern wall depicted the city of Shushan (Susa) — because the Jews built the Second Temple with permission from the Persian king, they commemorated this by engraving his capital city on the gate.",
      },
      status: "published",
      sortOrder: 1,
    },
    {
      learningDayId: day2.id,
      contentType: "conceptual_image",
      sefer: "Beis HaBechirah",
      perek: 4,
      halachaStart: 1,
      halachaEnd: 3,
      title: "The Ascending Levels of Holiness",
      content: {
        caption:
          "Ten levels of holiness radiate outward from the Holy of Holies: from the Land of Israel to Jerusalem, from the Temple Mount to the Courtyard, each step inward demands greater sanctity.",
        altText: "Concentric diagram showing the ten levels of holiness in the Temple",
      },
      imageUrl: "https://placehold.co/800x500/1a1520/C5A059?text=Levels+of+Holiness",
      thumbnailUrl: "https://placehold.co/400x250/1a1520/C5A059?text=Holiness",
      status: "published",
      sortOrder: 2,
    },
  ]);

  // --- Day 3: Beis HaBechirah Perakim 7-8 + Kiddush HaChodesh 1 ---
  const [day3] = await db
    .insert(learningDays)
    .values({
      date: "2026-04-07",
      hebrewDate: "7 Nissan 5786",
      track1Perakim: [{ sefer: "Beis HaBechirah", perek: 3 }],
      track3Perakim: [
        { sefer: "Beis HaBechirah", perek: 7 },
        { sefer: "Beis HaBechirah", perek: 8 },
        { sefer: "Kiddush HaChodesh", perek: 1 },
      ],
    })
    .returning();

  await db.insert(contentItems).values([
    {
      learningDayId: day3.id,
      contentType: "perek_overview",
      sefer: "Beis HaBechirah",
      perek: 7,
      title: "The Temple Mount and Its Guard",
      content: {
        text: "Perek 7 describes the duty to guard the Temple — not for security from enemies, but as an honor to the sacred place. The Kohanim and Levi'im stood guard at 24 posts throughout the night. Sleeping on watch duty was a serious offense.",
      },
      status: "published",
      sortOrder: 0,
    },
    {
      learningDayId: day3.id,
      contentType: "did_you_know",
      sefer: "Beis HaBechirah",
      perek: 7,
      title: "Did You Know?",
      content: {
        text: "The Temple guard was not for protection — it was a mark of honor. A palace without sentries is not a palace. The Levi'im guarded the Temple Mount from outside, while the Kohanim guarded from within.",
      },
      status: "published",
      sortOrder: 1,
    },
    {
      learningDayId: day3.id,
      contentType: "perek_overview",
      sefer: "Kiddush HaChodesh",
      perek: 1,
      title: "Sanctifying the New Month",
      content: {
        text: "This perek introduces the mitzvah of sanctifying the new month (Kiddush HaChodesh). The Jewish calendar is lunar-based, and the Sanhedrin in Jerusalem had the exclusive authority to declare the beginning of each month based on eyewitness testimony of the new moon.",
      },
      status: "published",
      sortOrder: 2,
    },
  ]);

  console.log(`Seeded 3 days, ${8 + 3 + 3} content items, 2 sichos references`);
  await pool.end();
}

seed().catch((err) => {
  console.error("Seed failed:", err);
  process.exit(1);
});
