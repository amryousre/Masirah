import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";

import { routing } from "@/i18n/routing";
import { getAccess } from "@/lib/adapters/session";
import { readRetention } from "@/lib/adapters/settings";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";

import { SettingsScreen } from "./settings-screen";
import styles from "./settings.module.css";

export async function generateMetadata({
  params,
}: PageProps<"/[lang]/settings">): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "settings" });
  return { title: t("title") };
}

// Settings (T102): the interface language, the organisation's retention period, and deleting a
// candidate's data when they ask (FR-028, FR-029, FR-076).
export default async function SettingsPage({ params }: PageProps<"/[lang]/settings">) {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  // The layout redirects anyone who is not a member, but renders alongside this page.
  if ((await getAccess()).kind !== "member") return null;
  const t = await getTranslations({ locale: lang, namespace: "settings" });
  const retention = await readRetention(await createSupabaseServerClient());

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>{t("title")}</h1>
      <SettingsScreen retention={retention} />
    </div>
  );
}
