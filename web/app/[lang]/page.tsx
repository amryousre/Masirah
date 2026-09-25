import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";

import { redirect } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";

// The start of the app is the jobs list. Its layout sends anyone not signed in to sign-in.
export default async function Home({ params }: PageProps<"/[lang]">) {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  redirect({ href: "/jobs", locale: lang });
}
