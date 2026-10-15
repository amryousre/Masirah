import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { SENTRY_TUNNEL } from "@/next.config";

// The browser sends its errors to the tunnel on this site (T031). The proxy must leave it alone:
// otherwise it would be treated as a page and redirected to a language, and every report lost.
// The matcher is read from proxy.ts's source, since importing the proxy loads Next.js's server.

function matcher(): RegExp {
  const source = readFileSync(new URL("../../proxy.ts", import.meta.url), "utf8");
  const literal = /matcher:\s*("(?:[^"\\]|\\.)*")/.exec(source)?.[1];
  if (literal === undefined) throw new Error("proxy.ts has no matcher");
  return new RegExp(`^${JSON.parse(literal) as string}$`);
}

describe("the error tracking tunnel", () => {
  it("is not handled by the proxy", () => {
    expect(matcher().test(SENTRY_TUNNEL)).toBe(false);
  });

  it("still leaves every page to the proxy", () => {
    expect(matcher().test("/ar/jobs")).toBe(true);
    expect(matcher().test("/en")).toBe(true);
  });
});
