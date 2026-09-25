import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";

import { routing } from "@/i18n/routing";

import styles from "./jobs.module.css";

export async function generateMetadata({ params }: PageProps<"/[lang]/jobs">): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "jobs" });
  return { title: t("title") };
}

// Where sign-in lands. The list itself, with its empty state, is T058.
export default async function JobsPage({ params }: PageProps<"/[lang]/jobs">) {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "jobs" });
  return (
    <div className={styles.page}>
      <h1 className={styles.title}>{t("title")}</h1>
    </div>
  );
}
