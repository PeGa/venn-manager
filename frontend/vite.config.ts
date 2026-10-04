import tailwindcss from "@tailwindcss/vite";
import solid from "vite-plugin-solid";
import { defineConfig } from "vitest/config";

// Only the one variable this config reads; avoids pulling in @types/node.
declare const process: { env: Record<string, string | undefined> };

/** Where /api goes. Defaults to a local backend; compose points it at the backend service. */
const API_URL = process.env["VENN_API_URL"] ?? "http://127.0.0.1:8000";

/** Extra host names the browser may use (comma-separated), e.g. "temple,venn-manager.kosumo". */
const ALLOWED_HOSTS = (process.env["VENN_ALLOWED_HOSTS"] ?? "")
  .split(",")
  .map((host) => host.trim())
  .filter((host) => host !== "");

export default defineConfig({
  plugins: [solid(), tailwindcss()],
  resolve: {
    alias: { "@": "/src" },
  },
  server: {
    // Same origin for the browser, so the session cookie stays SameSite=Lax.
    proxy: { "/api": API_URL },
    allowedHosts: ALLOWED_HOSTS,
  },
  preview: {
    proxy: { "/api": API_URL },
    allowedHosts: ALLOWED_HOSTS,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["tests/setup.ts"],
    coverage: {
      provider: "v8",
      include: ["src/domain/**", "src/adapters/**", "src/l10n/**"],
      thresholds: { lines: 70, functions: 70, branches: 70, statements: 70 },
    },
  },
});
