import { beforeEach, describe, expect, test } from "vitest";
import { clearAll } from "./helpers";
import app from "../src/app";
import { db } from "./setup";
import { whatsappSubscribers } from "../src/schema";
import { eq } from "drizzle-orm";

describe("WhatsApp webhook", () => {
  beforeEach(async () => {
    await clearAll();
  });

  async function postWebhook(body: Record<string, string>) {
    const formData = new URLSearchParams(body).toString();
    return app.request("/api/webhook/whatsapp", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData,
    });
  }

  describe("POST /api/webhook/whatsapp", () => {
    test("subscribes a new user", async () => {
      const res = await postWebhook({
        From: "whatsapp:+15551234567",
        Body: "join",
        WaId: "+15551234567",
      });

      expect(res.status).toBe(200);
      const text = await res.text();
      expect(text).toContain("Welcome to Merkos Rambam");

      const subs = await db.select().from(whatsappSubscribers);
      expect(subs).toHaveLength(1);
      expect(subs[0].status).toBe("active");
    });

    test("unsubscribes an existing user", async () => {
      // First subscribe
      await postWebhook({
        From: "whatsapp:+15559876543",
        Body: "subscribe",
      });

      // Then unsubscribe
      const res = await postWebhook({
        From: "whatsapp:+15559876543",
        Body: "stop",
      });

      expect(res.status).toBe(200);
      const text = await res.text();
      expect(text).toContain("unsubscribed");
    });

    test("changes track preference", async () => {
      await postWebhook({
        From: "whatsapp:+15551111111",
        Body: "join",
      });

      const res = await postWebhook({
        From: "whatsapp:+15551111111",
        Body: "1",
      });

      expect(res.status).toBe(200);
      const text = await res.text();
      expect(text).toContain("1-perek");
    });

    test("returns help message for unknown input", async () => {
      const res = await postWebhook({
        From: "whatsapp:+15552222222",
        Body: "hello there",
      });

      expect(res.status).toBe(200);
      const text = await res.text();
      expect(text).toContain("Merkos Rambam");
      expect(text).toContain("JOIN");
    });

    test("returns error for missing phone number", async () => {
      const res = await postWebhook({ Body: "join" });

      expect(res.status).toBe(200);
      const text = await res.text();
      expect(text).toContain("Missing phone number");
    });

    test("re-subscribes inactive user", async () => {
      await postWebhook({
        From: "whatsapp:+15553333333",
        Body: "join",
      });
      await postWebhook({
        From: "whatsapp:+15553333333",
        Body: "stop",
      });

      const res = await postWebhook({
        From: "whatsapp:+15553333333",
        Body: "start",
      });

      expect(res.status).toBe(200);
      const text = await res.text();
      expect(text).toContain("Welcome");
    });
  });
});
