import { migrate } from "drizzle-orm/node-postgres/migrator";
import {
  PostgreSqlContainer,
  StartedPostgreSqlContainer,
} from "@testcontainers/postgresql";
import { beforeAll, afterAll, vi } from "vitest";
import { Pool } from "pg";
import { drizzle } from "drizzle-orm/node-postgres";

let container: StartedPostgreSqlContainer;
let pool: Pool;
let db: ReturnType<typeof drizzle>;

vi.mock("../src/db", () => ({
  get db() {
    return db;
  },
  get pool() {
    return pool;
  },
}));

beforeAll(async () => {
  // Start Postgres container
  container = await new PostgreSqlContainer("postgres:18")
    .withDatabase("test_db")
    .start();

  // Create connection pool
  pool = new Pool({
    connectionString: container.getConnectionUri(),
  });

  db = drizzle({ client: pool });

  // Run migrations
  await migrate(db, { migrationsFolder: "./drizzle" });
}, 60000); // Timeout for container startup

afterAll(async () => {
  await pool.end();
  await container.stop();
});

export { db, pool };
