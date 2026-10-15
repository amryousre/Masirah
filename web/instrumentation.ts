import * as Sentry from "@sentry/nextjs";

import { sentryOptions } from "@/lib/adapters/telemetry";

// Error tracking on the server and the edge (T031). Sentry stays off without a DSN, so a local
// run or a test build sends nothing.
export function register(): void {
  Sentry.init(sentryOptions());
}

// Errors thrown while rendering a page, in a route handler or in the proxy.
export const onRequestError = Sentry.captureRequestError;
