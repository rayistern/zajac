import { z, createRoute } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";

const perekRoute = createRoute({
  method: "get",
  path: "/{sefer}/{perek}",
  request: {
    params: z.object({
      sefer: z.string(),
      perek: z.coerce.number().int().positive(),
    }),
  },
  responses: {
    200: {
      description: "Rambam perek text from Sefaria",
      content: {
        "application/json": {
          schema: z.object({
            sefer: z.string(),
            perek: z.number(),
            halachot: z.array(
              z.object({
                number: z.number(),
                he: z.string(),
                en: z.string(),
              }),
            ),
          }),
        },
      },
    },
    502: { description: "Sefaria API error" },
  },
});

const halachaRoute = createRoute({
  method: "get",
  path: "/{sefer}/{perek}/{halacha}",
  request: {
    params: z.object({
      sefer: z.string(),
      perek: z.coerce.number().int().positive(),
      halacha: z.coerce.number().int().positive(),
    }),
  },
  responses: {
    200: {
      description: "Single halacha text",
      content: {
        "application/json": {
          schema: z.object({
            number: z.number(),
            he: z.string(),
            en: z.string(),
          }),
        },
      },
    },
    404: { description: "Halacha not found" },
    502: { description: "Sefaria API error" },
  },
});

async function fetchFromSefaria(ref: string) {
  const url = `https://www.sefaria.org/api/v3/texts/${encodeURIComponent(ref)}?version=all`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Sefaria returned ${res.status}`);
  return res.json();
}

function buildSefariaRef(sefer: string, perek: number): string {
  const formatted = sefer.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return `Mishneh Torah, ${formatted} ${perek}`;
}

export const rambamRoutes = new OpenAPIHono()
  .openapi(perekRoute, async (c) => {
    const { sefer, perek } = c.req.valid("param");
    try {
      const ref = buildSefariaRef(sefer, perek);
      const data = await fetchFromSefaria(ref);

      const heTexts: string[] = data.versions?.find((v: any) => v.language === "he")?.text ?? [];
      const enTexts: string[] = data.versions?.find((v: any) => v.language === "en")?.text ?? [];

      const halachot = heTexts.map((he: string, i: number) => ({
        number: i + 1,
        he,
        en: enTexts[i] ?? "",
      }));

      return c.json({ sefer, perek, halachot }, 200);
    } catch {
      return c.json({ error: "Failed to fetch from Sefaria" }, 502);
    }
  })
  .openapi(halachaRoute, async (c) => {
    const { sefer, perek, halacha } = c.req.valid("param");
    try {
      const ref = `${buildSefariaRef(sefer, perek)}:${halacha}`;
      const data = await fetchFromSefaria(ref);

      const he = data.versions?.find((v: any) => v.language === "he")?.text ?? "";
      const en = data.versions?.find((v: any) => v.language === "en")?.text ?? "";

      if (!he) return c.json({ error: "Halacha not found" }, 404);
      return c.json({ number: halacha, he, en }, 200);
    } catch {
      return c.json({ error: "Failed to fetch from Sefaria" }, 502);
    }
  });
