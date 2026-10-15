import type { Breadcrumb, BrowserOptions, ErrorEvent } from "@sentry/nextjs";
import { captureException } from "@sentry/nextjs";

/**
 * Structured logs and error tracking for the web app (NFR-14, T031).
 *
 * Errors go to Sentry, EU region, when NEXT_PUBLIC_SENTRY_DSN is set; the DSN is not a secret,
 * since the browser sends its errors with it. Nothing a recruiter typed or a candidate wrote may
 * go with them: a search's query string can hold a candidate's name, so every URL loses its query
 * and fragment, and of a request only its bare URL is kept. Performance tracing and session
 * replay stay off: errors are what NFR-14 asks for, and a replay would record candidates' CVs.
 */

/** A URL without its query string and fragment. */
export function scrubUrl(url: string): string {
  const end = url.search(/[?#]/);
  return end === -1 ? url : url.slice(0, end);
}

const URL_FIELDS = ["url", "from", "to"] as const;

function scrubCrumb(breadcrumb: Breadcrumb): Breadcrumb {
  if (breadcrumb.data === undefined) return breadcrumb;
  const data: Record<string, unknown> = { ...breadcrumb.data };
  for (const field of URL_FIELDS) {
    const value = data[field];
    if (typeof value === "string") data[field] = scrubUrl(value);
  }
  return { ...breadcrumb, data };
}

/** Sentry's beforeBreadcrumb: no record of what was typed, and URLs without their queries. */
export function scrubBreadcrumb(breadcrumb: Breadcrumb): Breadcrumb | null {
  if (breadcrumb.category === "ui.input") return null;
  return scrubCrumb(breadcrumb);
}

/** Sentry's beforeSend: no user, and of the request only its URL, without its query. */
export function scrubEvent(event: ErrorEvent): ErrorEvent {
  const scrubbed: ErrorEvent = { ...event };
  delete scrubbed.user;
  delete scrubbed.request;
  if (event.request?.url !== undefined) scrubbed.request = { url: scrubUrl(event.request.url) };
  if (event.breadcrumbs !== undefined) scrubbed.breadcrumbs = event.breadcrumbs.map(scrubCrumb);
  return scrubbed;
}

/** The options every runtime starts Sentry with: the browser, the server and the edge. */
export function sentryOptions(): BrowserOptions {
  // Read where each runtime can see it: Next.js inlines NEXT_PUBLIC_ values into the browser
  // bundle at build time.
  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN ?? "";
  return {
    dsn,
    enabled: dsn !== "",
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT?.trim() || "production",
    // Every category of collected data is on by default; scrubEvent is the second line.
    dataCollection: {
      userInfo: false,
      cookies: false,
      httpHeaders: false,
      httpBodies: [],
      urlQueryParams: false,
      stackFrameVariables: false,
    },
    tracesSampleRate: 0,
    beforeSend: scrubEvent,
    beforeBreadcrumb: scrubBreadcrumb,
  };
}

type Level = "info" | "warn" | "error";
type Fields = Record<string, string | number | boolean | null>;

/**
 * One log line as a JSON object, which a host's log search can filter by field. Fields carry
 * identifiers and codes, never what a person typed.
 */
export function logEvent(level: Level, event: string, fields: Fields = {}): void {
  const line = JSON.stringify({ time: new Date().toISOString(), level, event, ...fields });
  console[level](line);
}

/**
 * An error worth an operator's attention: logged, and sent to Sentry with the same fields. Without
 * an error object, one named after the event is sent, so the report still groups by event.
 */
export function reportError(event: string, fields: Fields = {}, error?: unknown): void {
  logEvent("error", event, fields);
  captureException(error ?? new Error(event), { extra: fields });
}
