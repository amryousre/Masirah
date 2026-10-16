import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL(".", import.meta.url)),
      // The Word preview runs only in the browser, where mammoth's browser build takes an
      // ArrayBuffer; the Node build vitest would pick takes a Buffer. Test what ships.
      mammoth: "mammoth/mammoth.browser.js",
    },
  },
  test: {
    include: ["tests/unit/**/*.test.{ts,tsx}"],
    // Component tests opt into a DOM with a `@vitest-environment jsdom` comment.
    environment: "node",
    setupFiles: ["tests/unit/setup.ts"],
    css: { modules: { classNameStrategy: "non-scoped" } },
  },
});
