import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";

import { JobForm } from "./job-form";
import styles from "./new-job.module.css";

export async function generateMetadata({
  params,
}: PageProps<"/[lang]/jobs/new">): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "newJob" });
  return { title: t("title") };
}

// Creating a job (T059). The layout above has already checked the session.
export default async function NewJobPage({ params, searchParams }: PageProps<"/[lang]/jobs/new">) {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "newJob" });
  const { start } = await searchParams;
  return (
    <div className={styles.page}>
      <nav aria-label={t("breadcrumb")}>
        <Link href="/jobs" className={styles.back}>
          {t("back")}
        </Link>
      </nav>
      <h1 className={styles.title}>{t("title")}</h1>
      <JobForm start={start === "manual" ? "manual" : "paste"} />
    </div>
  );
}
