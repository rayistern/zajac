#!/usr/bin/env bash
# Demo launcher — spins up a local full-stack environment without AWS.
#
# Requires:
#   - Docker running
#   - pnpm install already done at repo root
#
# Usage: ./scripts/demo.sh
#
# After this runs:
#   - Postgres on localhost:5433 (container: pipeline-db)
#   - API on localhost:3000
#   - Frontend dev server on localhost:5173
#   - Open http://localhost:5173 in your browser

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Checking Postgres container"
if ! docker ps --filter "name=pipeline-db" --filter "status=running" --format "{{.Names}}" | grep -q pipeline-db; then
  echo "Starting Postgres 18 container on port 5433"
  docker run -d --name pipeline-db \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=merkos_rambam \
    -p 5433:5432 \
    postgres:18 || docker start pipeline-db
  sleep 2
fi

echo "==> Ensuring 'app' database exists"
docker exec pipeline-db psql -U postgres -c "CREATE DATABASE app;" 2>/dev/null || true

echo "==> Resetting postgres password"
docker exec pipeline-db psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';" > /dev/null

echo "==> Applying Drizzle migrations to app DB"
cat api/drizzle/*/migration.sql | docker exec -i pipeline-db psql -U postgres -d app > /dev/null 2>&1 || true

echo "==> Seeding content (idempotent — truncates first)"
docker exec pipeline-db psql -U postgres -d app -c \
  "TRUNCATE TABLE content_item, learning_day, sichos_reference, share_event, user_preference, whatsapp_subscriber RESTART IDENTITY CASCADE;" > /dev/null
TSX="$REPO_ROOT/node_modules/.pnpm/tsx@4.21.0/node_modules/tsx/dist/cli.mjs"
(cd api && "$TSX" --env-file=.env.dev scripts/seed-content.ts)

echo ""
echo "==> Starting API (port 3000)"
cd api
node --env-file=.env.dev \
  --import=/home/rayi/repos/zajac/node_modules/.pnpm/tsx@4.21.0/node_modules/tsx/dist/loader.mjs \
  src/index.ts > /tmp/merkos-api.log 2>&1 &
API_PID=$!
cd ..

# Wait for API to be ready
for i in {1..10}; do
  if curl -s http://localhost:3000/ > /dev/null 2>&1; then
    echo "    API ready at http://localhost:3000"
    break
  fi
  sleep 1
done

echo ""
echo "==> Starting frontend dev server (port 5173)"
echo ""
echo "=============================================="
echo "  Open http://localhost:5173 in your browser"
echo "=============================================="
echo ""
echo "API log: tail -f /tmp/merkos-api.log"
echo "To stop API: kill $API_PID"
echo ""

trap "kill $API_PID 2>/dev/null || true" EXIT

pnpm --filter frontend run dev
