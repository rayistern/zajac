import { z, createRoute } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { eq } from "drizzle-orm";
import { db } from "../db";
import { whatsappSubscribers } from "../schema/whatsapp";
import crypto from "node:crypto";

const SUBSCRIBE_KEYWORDS = ["subscribe", "join", "start", "הצטרף"];
const UNSUBSCRIBE_KEYWORDS = ["unsubscribe", "stop", "leave", "הפסק"];
const TRACK_KEYWORDS: Record<string, string> = {
  "1": "1-perek",
  "one": "1-perek",
  "3": "3-perek",
  "three": "3-perek",
};

const whatsappWebhookRoute = createRoute({
  method: "post",
  path: "/whatsapp",
  request: {
    body: {
      content: {
        "application/x-www-form-urlencoded": {
          schema: z.object({
            From: z.string().optional(),
            Body: z.string().optional(),
            WaId: z.string().optional(),
            ProfileName: z.string().optional(),
          }),
        },
      },
    },
  },
  responses: {
    200: {
      description: "TwiML response",
      content: { "text/xml": { schema: z.string() } },
    },
  },
});

export const webhookRoutes = new OpenAPIHono().openapi(
  whatsappWebhookRoute,
  async (c) => {
    const body = c.req.valid("form");
    const phone = body.From || body.WaId || "";
    const message = (body.Body || "").trim().toLowerCase();

    if (!phone) {
      return c.text(twiml("Missing phone number."), 200, {
        "Content-Type": "text/xml",
      });
    }

    const phoneHash = crypto
      .createHash("sha256")
      .update(phone)
      .digest("hex")
      .slice(0, 32);

    // Handle subscribe
    if (SUBSCRIBE_KEYWORDS.some((kw) => message.includes(kw))) {
      const existing = await db
        .select()
        .from(whatsappSubscribers)
        .where(eq(whatsappSubscribers.phoneHash, phoneHash))
        .limit(1);

      if (existing.length > 0) {
        await db
          .update(whatsappSubscribers)
          .set({ status: "active", unsubscribedAt: null })
          .where(eq(whatsappSubscribers.phoneHash, phoneHash));
      } else {
        await db.insert(whatsappSubscribers).values({
          phoneHash,
          track: "3-perek",
          status: "active",
        });
      }

      return c.text(
        twiml(
          "Welcome to Merkos Rambam! You'll receive daily content. Reply STOP to unsubscribe, or 1 or 3 to change your track.",
        ),
        200,
        { "Content-Type": "text/xml" },
      );
    }

    // Handle unsubscribe
    if (UNSUBSCRIBE_KEYWORDS.some((kw) => message.includes(kw))) {
      await db
        .update(whatsappSubscribers)
        .set({ status: "inactive", unsubscribedAt: new Date() })
        .where(eq(whatsappSubscribers.phoneHash, phoneHash));

      return c.text(
        twiml(
          "You've been unsubscribed from Merkos Rambam. Reply JOIN to re-subscribe anytime.",
        ),
        200,
        { "Content-Type": "text/xml" },
      );
    }

    // Handle track change
    const trackKey = Object.keys(TRACK_KEYWORDS).find((kw) =>
      message.includes(kw),
    );
    if (trackKey) {
      const track = TRACK_KEYWORDS[trackKey];
      await db
        .update(whatsappSubscribers)
        .set({ track })
        .where(eq(whatsappSubscribers.phoneHash, phoneHash));

      return c.text(
        twiml(`Track updated to ${track}. You'll receive content for this track.`),
        200,
        { "Content-Type": "text/xml" },
      );
    }

    // Default response
    return c.text(
      twiml(
        "Merkos Rambam — Daily Rambam learning. Reply JOIN to subscribe, STOP to unsubscribe, or 1/3 to change your track.",
      ),
      200,
      { "Content-Type": "text/xml" },
    );
  },
);

function twiml(message: string): string {
  return `<?xml version="1.0" encoding="UTF-8"?><Response><Message>${escapeXml(message)}</Message></Response>`;
}

function escapeXml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
