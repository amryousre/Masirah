import { expect, test } from "@playwright/test";

// GET /api/health (T030) against the running app and its database: no sign-in needed, never
// cached, a status that matches its HTTP code, and nothing but aggregate figures.

test("reports the queue and the worker without signing in", async ({ request }) => {
  const response = await request.get("/api/health");
  const body = (await response.json()) as Record<string, unknown>;

  expect(["ok", "degraded"]).toContain(body["status"]);
  expect(response.status()).toBe(body["status"] === "ok" ? 200 : 503);
  expect(response.headers()["cache-control"]).toContain("no-store");
  expect(typeof body["queueDepth"]).toBe("number");
  expect(Object.keys(body).sort()).toEqual([
    "heartbeatAgeSeconds",
    "oldestMessageSeconds",
    "problems",
    "queueDepth",
    "status",
  ]);
});
