import type { NextRequest } from "next/server";
import createMiddleware from "next-intl/middleware";

import { routing } from "./i18n/routing";
import { createSupabaseClient } from "./lib/adapters/supabase";

// Detection and redirect (T025): a path without a locale goes to the visitor's language, taken
// from the locale cookie or Accept-Language, and to Arabic when neither says.
const handleI18nRouting = createMiddleware(routing);

export default async function proxy(request: NextRequest) {
  const response = handleI18nRouting(request);

  // Keeps the session alive (T024). An expired access token is refreshed here, because pages
  // cannot write cookies; the new cookies go on the response, and Next.js passes them on to the
  // page rendering this same request. This is not an access check: every page checks for itself.
  const supabase = createSupabaseClient({
    getAll: () => request.cookies.getAll(),
    setAll: (toSet, headers) => {
      for (const { name, value, options } of toSet) response.cookies.set(name, value, options);
      // Responses that set auth cookies must not be cached, or one user's session could be
      // served to another.
      for (const [name, value] of Object.entries(headers)) response.headers.set(name, value);
    },
  });
  await supabase.auth.getClaims();

  return response;
}

export const config = {
  // Every path except API routes, Next.js internals, the error tracking tunnel (SENTRY_TUNNEL in
  // next.config.ts) and files with an extension.
  matcher: "/((?!api|_next|_vercel|monitoring|.*\\..*).*)",
};
