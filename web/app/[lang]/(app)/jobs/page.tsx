import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";

import { ButtonLink } from "@/components/button/button-link";
import { JobTable } from "@/components/jobs/job-table";
import { routing } from "@/i18n/routing";
import { listJobs } from "@/lib/adapters/jobs";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";
import { MAX_BATCH_FILES } from "@/lib/domain/uploads";

import styles from "./jobs.module.css";

export async function generateMetadata({ params }: PageProps<"/[lang]/jobs">): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "jobs" });
  return { title: t("title") };
}

// Where sign-in lands (T058). With no jobs yet, the page teaches how a ranking comes about rather
// than reporting an absence (design-brief.md section 6).
export default async function JobsPage({ params }: PageProps<"/[lang]/jobs">) {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "jobs" });
  const jobs = await listJobs(await createSupabaseServerClient());

  if (jobs.length === 0) {
    return (
      <div className={styles.page}>
        <h1 className={styles.title}>{t("title")}</h1>
        <section className={styles.empty} aria-labelledby="no-jobs">
          <h2 id="no-jobs" className={styles.emptyTitle}>
            {t("empty.title")}
          </h2>
          <p className={styles.emptyBody}>{t("empty.body")}</p>
          <ol className={styles.steps}>
            <li>{t("empty.stepCreate")}</li>
            <li>{t("empty.stepDrop", { max: MAX_BATCH_FILES })}</li>
            <li>{t("empty.stepReview")}</li>
          </ol>
          <div className={styles.actions}>
            <ButtonLink href="/jobs/new" variant="primary">
              {t("createJob")}
            </ButtonLink>
            <ButtonLink href={{ pathname: "/jobs/new", query: { start: "paste" } }}>
              {t("pasteDescription")}
            </ButtonLink>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>{t("title")}</h1>
        <ButtonLink href="/jobs/new" variant="primary">
          {t("createJob")}
        </ButtonLink>
      </header>
      <JobTable jobs={jobs} locale={lang} now={new Date()} />
    </div>
  );
}
