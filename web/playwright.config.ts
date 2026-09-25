import { existsSync } from "node:fs";

import { defineConfig, devices } from "@playwright/test";

const isCI = process.env["CI"] !== undefined;

// Locally the Supabase settings come from the same file as the dev server, and the secret key
// the sign-in tests use to make accounts from .env.test.local, which the dev server never loads.
// CI sets all of them from `supabase status`.
for (const file of [".env.local", ".env.test.local"]) {
  if (existsSync(file)) process.loadEnvFile(file);
}

export default defineConfig({
  testDir: "tests/e2e",
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  reporter: isCI ? "github" : "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    // CI tests the production build it has just made; locally the dev server is quicker to start.
    command: isCI ? "npm run start" : "npm run dev",
    url: "http://localhost:3000/ar/design",
    reuseExistingServer: !isCI,
  },
});
