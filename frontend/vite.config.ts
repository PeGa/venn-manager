import tailwindcss from "@tailwindcss/vite";
import solid from "vite-plugin-solid";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [solid(), tailwindcss()],
  resolve: {
    alias: { "@": "/src" },
  },
  server: {
    // Same origin for the browser, so the session cookie stays SameSite=Lax.
    proxy: { "/api": "http://127.0.0.1:8000" },
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
