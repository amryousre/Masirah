import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL(".", import.meta.url)) },
  },
  test: {
    include: ["tests/unit/**/*.test.{ts,tsx}"],
    // Component tests opt into a DOM with a `@vitest-environment jsdom` comment.
    environment: "node",
    setupFiles: ["tests/unit/setup.ts"],
    css: { modules: { classNameStrategy: "non-scoped" } },
  },
});
