import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";
import { notFound } from "next/navigation";
import * as rootParams from "next/root-params";

import { type Locale, routing } from "./routing";

const messages = {
  ar: () => import("../messages/ar.json"),
  en: () => import("../messages/en.json"),
} satisfies Record<Locale, () => Promise<unknown>>;

export default getRequestConfig(async ({ locale: requested }) => {
  // A caller may name the locale explicitly; otherwise it is the [lang] segment of the route.
  const locale = requested ?? (await rootParams.lang());
  if (!hasLocale(routing.locales, locale)) notFound();
  return { locale, messages: (await messages[locale]()).default };
});
