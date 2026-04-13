/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";

// https://vite.dev/config/
export default defineConfig(() => {
  const routesDir = resolve(__dirname, "src/routes");

  return {
    plugins: [
      existsSync(routesDir)
        ? tanstackRouter({
            target: "react",
            autoCodeSplitting: true,
          })
        : null,
      tailwindcss(),
      react(),
    ].filter(Boolean),
    test: {
      coverage: {
        include: ["src/**/*.{ts,tsx}"],
        reporter: ["text", "html", "json-summary"],
      },
    },
    server: {
      proxy: {
        "/api": "http://localhost:3000",
      },
    },
  };
});
