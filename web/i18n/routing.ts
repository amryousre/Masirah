import { defineRouting } from "next-intl/routing";

// Arabic is the original and the default; English is the second language (Constitution IV).
// The locale is always in the path, so a shared link opens in the language it was sent in.
export const routing = defineRouting({
  locales: ["ar", "en"],
  defaultLocale: "ar",
  localePrefix: "always",
});

export type Locale = (typeof routing.locales)[number];

const directions = { ar: "rtl", en: "ltr" } as const satisfies Record<Locale, "rtl" | "ltr">;

/** The one place the reading direction is decided (T025). Everything else inherits `dir`. */
export function direction(locale: Locale): "rtl" | "ltr" {
  return directions[locale];
}
