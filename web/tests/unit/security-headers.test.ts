import { describe, expect, it } from "vitest";

import config from "@/next.config";

// The app sends its own security headers on every response, pages from the server included, so
// they hold on any host (T032: no code may depend on Netlify, ADR 0002).

async function headersFor(path: string): Promise<Record<string, string>> {
  const rules = (await config.headers?.()) ?? [];
  const matching = rules.filter((rule) => rule.source === "/:path*");
  expect(matching, `no rule covers ${path}`).not.toHaveLength(0);
  return Object.fromEntries(matching.flatMap((rule) => rule.headers).map((h) => [h.key, h.value]));
}

describe("security headers", () => {
  it("forbid any other site from framing the app", async () => {
    const headers = await headersFor("/ar/jobs");
    expect(headers["Content-Security-Policy"]).toContain("frame-ancestors 'none'");
    expect(headers["X-Frame-Options"]).toBe("DENY");
  });

  it("stop MIME sniffing, keep referrers to the origin and turn off device access", async () => {
    const headers = await headersFor("/en/sign-in");
    expect(headers["X-Content-Type-Options"]).toBe("nosniff");
    expect(headers["Referrer-Policy"]).toBe("strict-origin-when-cross-origin");
    expect(headers["Permissions-Policy"]).toBe("camera=(), microphone=(), geolocation=()");
  });

  it("keep the app out of search results while access is by invitation", async () => {
    expect((await headersFor("/en/privacy"))["X-Robots-Tag"]).toBe("noindex");
  });
});
