import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";

import { redirect } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";

// Until sign-in (T024) and the jobs list exist, the start of the app is the design system, so
// the shared components can be seen in the browser in both languages.
export default async function Home({ params }: PageProps<"/[lang]">) {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  redirect({ href: "/design", locale: lang });
}
