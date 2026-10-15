import type { Breadcrumb, ErrorEvent } from "@sentry/nextjs";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  logEvent,
  scrubBreadcrumb,
  scrubEvent,
  scrubUrl,
  sentryOptions,
} from "@/lib/adapters/telemetry";

// Structured logs and error tracking for the web app (NFR-14, T031). Errors go to Sentry, EU
// region, and nothing a recruiter typed or a candidate wrote may go with them: a search's query
// string can hold a candidate's name, so every URL loses its query and fragment, and the request
// body, cookies, headers and user are dropped.

describe("scrubUrl", () => {
  it("keeps the path and drops the query and fragment", () => {
    expect(scrubUrl("https://masirah.online/ar/jobs/1?q=محمد#evidence")).toBe(
      "https://masirah.online/ar/jobs/1",
    );
  });

  it("does the same for a relative URL", () => {
    expect(scrubUrl("/en/review?file=abc&q=name")).toBe("/en/review");
  });

  it("leaves a URL with neither untouched", () => {
    expect(scrubUrl("/en/settings")).toBe("/en/settings");
  });
});

describe("scrubEvent", () => {
  const event = (): ErrorEvent => ({
    type: undefined,
    message: "boom",
    user: { email: "recruiter@delta-soft.com", ip_address: "1.2.3.4" },
    request: {
      url: "https://masirah.online/ar/jobs?q=Nourhan",
      query_string: "q=Nourhan",
      cookies: { "sb-access-token": "secret" },
      headers: { cookie: "sb=secret", "user-agent": "x" },
      data: { email: "nourhan@delta-soft.com" },
    },
    breadcrumbs: [{ category: "navigation", data: { from: "/ar/jobs?q=x", to: "/ar/review?q=y" } }],
  });

  it("drops the user and everything a request carried but its bare URL", () => {
    const scrubbed = scrubEvent(event());
    expect(scrubbed.user).toBeUndefined();
    expect(scrubbed.request).toEqual({ url: "https://masirah.online/ar/jobs" });
  });

  it("scrubs the URLs in breadcrumbs", () => {
    const [crumb] = scrubEvent(event()).breadcrumbs ?? [];
    expect(crumb?.data).toEqual({ from: "/ar/jobs", to: "/ar/review" });
  });

  it("keeps the error itself", () => {
    expect(scrubEvent(event()).message).toBe("boom");
  });
});

describe("scrubBreadcrumb", () => {
  it("scrubs a fetch's URL and keeps its status", () => {
    const crumb: Breadcrumb = {
      category: "fetch",
      data: { url: "/api/jobs/1/candidates?q=x", method: "GET", status_code: 500 },
    };
    expect(scrubBreadcrumb(crumb)?.data).toEqual({
      url: "/api/jobs/1/candidates",
      method: "GET",
      status_code: 500,
    });
  });

  it("drops what was typed into the page", () => {
    expect(scrubBreadcrumb({ category: "ui.input", message: "input[name=q]" })).toBeNull();
  });
});

describe("sentryOptions", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("is off without a DSN", () => {
    vi.stubEnv("NEXT_PUBLIC_SENTRY_DSN", "");
    expect(sentryOptions().enabled).toBe(false);
  });

  it("sends errors only, without personal data, when a DSN is set", () => {
    vi.stubEnv("NEXT_PUBLIC_SENTRY_DSN", "https://key@o1.ingest.de.sentry.io/2");
    const options = sentryOptions();
    expect(options.enabled).toBe(true);
    expect(options.dsn).toBe("https://key@o1.ingest.de.sentry.io/2");
    expect(options.dataCollection).toEqual({
      userInfo: false,
      cookies: false,
      httpHeaders: false,
      httpBodies: [],
      urlQueryParams: false,
      stackFrameVariables: false,
    });
    expect(options.tracesSampleRate).toBe(0);
    expect(options.beforeSend).toBeTypeOf("function");
    expect(options.beforeBreadcrumb).toBeTypeOf("function");
  });

  it("names the environment, production by default", () => {
    vi.stubEnv("NEXT_PUBLIC_SENTRY_DSN", "https://key@o1.ingest.de.sentry.io/2");
    expect(sentryOptions().environment).toBe("production");
    vi.stubEnv("NEXT_PUBLIC_SENTRY_ENVIRONMENT", " ");
    expect(sentryOptions().environment).toBe("production");
    vi.stubEnv("NEXT_PUBLIC_SENTRY_ENVIRONMENT", "preview");
    expect(sentryOptions().environment).toBe("preview");
  });
});

describe("logEvent", () => {
  it("writes one JSON line with the event, its fields and the time", () => {
    const write = vi.spyOn(console, "error").mockImplementation(() => undefined);
    logEvent("error", "join_waitlist failed", { code: "53400" });
    expect(write).toHaveBeenCalledOnce();
    const line = JSON.parse(String(write.mock.calls[0]?.[0])) as Record<string, unknown>;
    expect(line).toMatchObject({ level: "error", event: "join_waitlist failed", code: "53400" });
    expect(line.time).toBeTypeOf("string");
    write.mockRestore();
  });

  it("writes information to the ordinary log", () => {
    const write = vi.spyOn(console, "info").mockImplementation(() => undefined);
    logEvent("info", "started");
    expect(write).toHaveBeenCalledOnce();
    write.mockRestore();
  });
});
