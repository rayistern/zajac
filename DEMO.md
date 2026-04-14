# Running the Demo

This project has a one-command demo that spins up the full stack locally — no AWS, no API keys, no cloud services required.

---

## Prerequisites

- **Docker** (for PostgreSQL 18 container)
- **Node.js 20+** and **pnpm 10.32.1** (via corepack)
- About 1 GB free disk space

### One-time setup

```bash
# Install Node deps
corepack enable
corepack prepare pnpm@10.32.1 --activate
pnpm install
```

---

## Running the demo

From the repo root:

```bash
./scripts/demo.sh
```

This will:

1. Start a PostgreSQL 18 container on port **5433** (named `pipeline-db`)
2. Create the `app` database
3. Run Drizzle migrations (creates 6 API tables)
4. Seed 3 days of sample content (today, yesterday, tomorrow)
5. Start the API on http://localhost:3000
6. Start the frontend dev server on http://localhost:5173

Open **http://localhost:5173** in a browser.

Press `Ctrl+C` to stop — this shuts down the frontend dev server and the API.

The Postgres container keeps running so your data persists between demo runs. To stop it:

```bash
docker rm -f pipeline-db
```

---

## Running the demo from another machine (headless server)

If your dev machine has no browser, you have three options:

### Option 1: SSH port forwarding (recommended)

From your laptop:

```bash
ssh -L 5173:localhost:5173 -L 3000:localhost:3000 <your-username>@<server-host>
```

Keep that SSH session open, then in a separate terminal on the server run:

```bash
./scripts/demo.sh
```

On your laptop, open **http://localhost:5173** — it'll transparently go through the SSH tunnel to the server.

### Option 2: Expose on your LAN

On the server, edit `frontend/vite.config.ts` to add `host: true`:

```ts
server: {
  host: true,  // listen on 0.0.0.0 instead of 127.0.0.1
  proxy: { "/api": "http://localhost:3000" },
}
```

Then run `./scripts/demo.sh` and access from another device on the same network at `http://<server-ip>:5173`.

**Note:** this exposes the dev server to your local network. Only do this on a trusted network.

### Option 3: Run entirely on the other machine

Clone the repo on your laptop, install Docker + pnpm there, and run `./scripts/demo.sh` locally.

---

## What you'll see

- **Home screen** (/) — Today's perakim, hero card, content feed with 5 items (images, infographics, overviews, "did you know"), sichos references
- **Track selector** — toggle between 1-perek and 3-perek tracks
- **Day view** (/day/YYYY-MM-DD) — navigate to a specific date with prev/next arrows
- **Dark theme** with Hebrew font support and mobile-first layout
- **PWA** — open Chrome DevTools → Application tab to see the service worker caching

---

## Troubleshooting

### "permission denied" on /var/run/docker.sock
Your user isn't in the `docker` group:

```bash
sudo usermod -aG docker $USER
# Log out and log back in, or run: newgrp docker
```

### "port 5432 already allocated"
Another Postgres container is using port 5432. The demo uses 5433 on purpose to avoid conflicts. If 5433 is also taken, edit `scripts/demo.sh` and the port mappings in `api/.env.dev`.

### "password authentication failed for user postgres"
Postgres password drift. Fix:

```bash
docker exec pipeline-db psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';"
```

### Frontend shows "No content for today"
The seed is date-relative — it always seeds today/yesterday/tomorrow. If you see this, the seed step failed. Check `/tmp/merkos-api.log` for errors, and try:

```bash
docker exec pipeline-db psql -U postgres -d app -c "SELECT date, hebrew_date FROM learning_day;"
```

You should see today's date in the list. If not, re-run `./scripts/demo.sh`.

### TanStack Router warning about test file
Harmless — test files under `frontend/src/routes/-*.tsx` are excluded from the route tree.

---

## What's in the demo data

- **3 days of content** for Hilchos Beis HaBechirah (sample data from Rambam)
- **14 content items** across all 6 content types (`perek_overview`, `conceptual_image`, `infographic`, `daily_chart`, `did_you_know`, `sichos_highlight`)
- **2 sichos references** from Likkutei Sichos
- All images are placehold.co placeholder URLs (not real AI-generated art)

The real pipeline (Python, in `pipeline/`) generates actual content from podcast RSS feeds, but that needs API keys for sofer.ai, OpenAI, Anthropic, Replicate, Telegram, and Twilio. See `TODO.md` for the deployment path.

---

## Architecture at a glance

```
┌──────────────┐    /api/*    ┌─────────┐    SQL    ┌──────────┐
│  Frontend    │ ───proxy───▶ │  Hono   │ ─────────▶│ Postgres │
│ (Vite :5173) │              │  API    │           │  :5433   │
│              │              │  :3000  │           │          │
└──────────────┘              └─────────┘           └──────────┘
   React 19                    Drizzle ORM          Docker
   TanStack Router             @hono/zod-openapi    (persistent volume)
   openapi-react-query
```

The real production stack swaps Vite for a pre-built static bundle on S3/CloudFront, and Postgres for RDS, but everything else is the same.
