import { drizzle } from "drizzle-orm/node-postgres";
import { Pool, PoolConfig } from "pg";
import { env } from "./env";
import * as schema from "./schema";

export const connectionConfig: PoolConfig = {
  host: env.DB_HOST,
  database: env.DB_NAME,
  user: env.DB_USER,
  password: env.DB_PASS,
};

export const pool = new Pool(connectionConfig);

export const db = drizzle({
  client: pool,
  schema,
});
