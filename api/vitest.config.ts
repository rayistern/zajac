import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    coverage: {
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/index.ts", "src/env.ts", "src/db.ts", "src/schema/index.ts"],
      reporter: ["text", "html", "json-summary"],
    },
    testTimeout: 30000,
  },
});
