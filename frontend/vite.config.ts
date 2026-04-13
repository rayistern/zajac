/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import { VitePWA } from "vite-plugin-pwa";

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
      VitePWA({
        registerType: "autoUpdate",
        includeAssets: ["favicon.svg", "apple-touch-icon.svg"],
        manifest: {
          name: "Merkos Rambam",
          short_name: "Rambam",
          description:
            "Daily Rambam learning with AI-generated visual content",
          theme_color: "#121212",
          background_color: "#121212",
          display: "standalone",
          orientation: "portrait",
          start_url: "/",
          icons: [
            {
              src: "pwa-192x192.svg",
              sizes: "192x192",
              type: "image/svg+xml",
            },
            {
              src: "pwa-512x512.svg",
              sizes: "512x512",
              type: "image/svg+xml",
            },
            {
              src: "pwa-512x512.svg",
              sizes: "512x512",
              type: "image/svg+xml",
              purpose: "any maskable",
            },
          ],
        },
        workbox: {
          globPatterns: ["**/*.{js,css,html,svg,woff2}"],
          runtimeCaching: [
            {
              urlPattern: /^\/api\/content\/.*/i,
              handler: "StaleWhileRevalidate",
              options: {
                cacheName: "api-content",
                expiration: {
                  maxEntries: 50,
                  maxAgeSeconds: 60 * 60 * 24, // 24 hours
                },
              },
            },
            {
              urlPattern: /^\/api\/rambam\/.*/i,
              handler: "CacheFirst",
              options: {
                cacheName: "api-rambam-text",
                expiration: {
                  maxEntries: 200,
                  maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
                },
              },
            },
            {
              urlPattern: /^\/api\/sichos\/.*/i,
              handler: "CacheFirst",
              options: {
                cacheName: "api-sichos",
                expiration: {
                  maxEntries: 200,
                  maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
                },
              },
            },
            {
              urlPattern: /\.(?:png|jpg|jpeg|webp|avif)$/i,
              handler: "CacheFirst",
              options: {
                cacheName: "content-images",
                expiration: {
                  maxEntries: 100,
                  maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
                },
              },
            },
            {
              urlPattern:
                /^https:\/\/fonts\.(?:googleapis|gstatic)\.com\/.*/i,
              handler: "CacheFirst",
              options: {
                cacheName: "google-fonts",
                expiration: {
                  maxEntries: 10,
                  maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
                },
              },
            },
          ],
        },
      }),
    ].filter(Boolean),
    test: {
      environment: "jsdom",
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
