/**
 * Use `--env-file=<>` flag to load an env file
 */
import { z } from "@hono/zod-openapi";

const envSchema = z.object({
  DB_HOST: z.string(),
  DB_PORT: z.coerce.number().default(5432),
  DB_NAME: z.string(),
  DB_USER: z.string(),
  DB_PASS: z.string(),
});

// [ ] standardize authorization model (ABAC with RBAC facade on top, allows for long term flexibility while starting with interface simplicity)
// [ ] standardize ontologies of (organizations)
// [ ] recommend git-ai?

// TODO: environment variable data shape should be enforced at the type
// level to match whatever is declared as `environment` in the infra folder
export const env = envSchema.parse(process.env);
