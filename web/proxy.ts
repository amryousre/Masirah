import createMiddleware from "next-intl/middleware";

import { routing } from "./i18n/routing";

// Detection and redirect (T025): a path without a locale goes to the visitor's language, taken
// from the locale cookie or Accept-Language, and to Arabic when neither says.
export default createMiddleware(routing);

export const config = {
  // Every path except API routes, Next.js internals and files with an extension.
  matcher: "/((?!api|_next|_vercel|.*\\..*).*)",
};
