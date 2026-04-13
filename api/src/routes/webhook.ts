import { z, createRoute } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";

const whatsappWebhookRoute = createRoute({
  method: "post",
  path: "/whatsapp",
  request: {
    body: {
      content: { "application/json": { schema: z.any() } },
    },
  },
  responses: {
    200: { description: "Webhook received" },
  },
});

export const webhookRoutes = new OpenAPIHono().openapi(
  whatsappWebhookRoute,
  async (c) => {
    // TODO: Implement Twilio WhatsApp webhook handler
    // - Parse incoming messages
    // - Handle subscribe/unsubscribe keywords
    // - Update whatsapp_subscribers table
    return c.json({ status: "ok" }, 200);
  },
);
