import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

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

export default withNextIntl(nextConfig);
