/// <reference types="vitest/config" />
import preact from "@preact/preset-vite";
import tailwindcss from "@tailwindcss/vite";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

// A default export is required by Vite's config loader; the "named exports only"
// rule in AGENTS.md covers application components and utilities.
// The function form is required: reading VITE_API_TARGET needs loadEnv, and
// neither `process` nor `import.meta.env` is available when Node evaluates the
// bundled config file.
export default defineConfig(({ mode }) => ({
  plugins: [preact(), tailwindcss()],
  resolve: {
    alias: { "@": new URL("./src", import.meta.url).pathname },
  },
  server: {
    port: 5173,
    // Single origin in the browser, so the session cookie can stay SameSite=Lax
    // (AGENTS.md § Authentication & Session Security). See docs/backend/
    // CONTRACT_NOTES.md § 10 for why flask-cors is deliberately absent.
    // VITE_API_TARGET lets a developer point the proxy at a non-default backend
    // (a scratch database, a second checkout) without editing this file.
    proxy: {
      "/api": {
        target: loadEnv(mode, ".", "VITE_").VITE_API_TARGET ?? "http://127.0.0.1:5000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["tests/**/*.test.ts", "tests/**/*.test.tsx"],
    setupFiles: ["tests/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      include: ["src/**"],
      exclude: ["src/main.tsx", "src/vite-env.d.ts"],
      // AGENTS.md § TDD: 70% minimum for frontend *logic*. Screens are rendered
      // through the same hooks and utilities, so they are reported but not gated.
      thresholds: {
        "src/utils/**": { lines: 70, functions: 70, branches: 70, statements: 70 },
        "src/api/**": { lines: 70, functions: 70, branches: 70, statements: 70 },
        "src/hooks/**": { lines: 70, functions: 70, branches: 70, statements: 70 },
        "src/l10n/**": { lines: 70, functions: 70, branches: 70, statements: 70 },
      },
    },
  },
}));
