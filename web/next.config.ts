import { withSentryConfig } from "@sentry/nextjs/config";
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

/** Where the browser sends its errors; proxy.ts must leave it alone. */
export const SENTRY_TUNNEL = "/monitoring";

// Sent on every response, pages from the server included, by the app itself, so they hold on any
// host (T032: no code may depend on Netlify, ADR 0002).
const securityHeaders = [
  // No other site may frame the app, so a recruiter's click cannot be hijacked.
  {
    key: "Content-Security-Policy",
    value: "frame-ancestors 'none'; base-uri 'self'; object-src 'none'",
  },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  // Access is by invitation and nothing is launched publicly yet, so nothing should be indexed.
  { key: "X-Robots-Tag", value: "noindex" },
];

const nextConfig: NextConfig = {
  headers: () => Promise.resolve([{ source: "/:path*", headers: securityHeaders }]),
};

// Error tracking (T031). The browser sends its errors to /monitoring on this site, which passes
// them to Sentry, so neither an ad blocker nor a future connect-src policy stops them. With
// SENTRY_AUTH_TOKEN set at build time the source maps are uploaded, for readable stack traces,
// and then deleted, so they are never served.
export default withSentryConfig(withNextIntl(nextConfig), {
  org: "amr-c2",
  project: "masirah-web",
  ...(process.env.SENTRY_AUTH_TOKEN === undefined
    ? {}
    : { authToken: process.env.SENTRY_AUTH_TOKEN }),
  tunnelRoute: SENTRY_TUNNEL,
  silent: !process.env.CI,
  telemetry: false,
});
