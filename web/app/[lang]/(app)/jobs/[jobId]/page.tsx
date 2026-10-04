import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { readJobPage } from "@/lib/adapters/job-page";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";
import { rankJob } from "@/lib/domain/ranking";

import { JobScreen } from "./job-screen";
import styles from "./job.module.css";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

async function load(lang: string, jobId: string) {
  if (!hasLocale(routing.locales, lang) || !UUID.test(jobId)) notFound();
  const page = await readJobPage(await createSupabaseServerClient(), jobId);
  // Another organisation's job is invisible under row level security, so it is simply not found.
  if (page === null) notFound();
  return { locale: lang, page };
}

export async function generateMetadata({
  params,
}: PageProps<"/[lang]/jobs/[jobId]">): Promise<Metadata> {
  const { lang, jobId } = await params;
  const { page } = await load(lang, jobId);
  return { title: page.job.title };
}

// A job's own page (T063): its ranked candidates, and the drop target that adds CVs to it (T062).
export default async function JobPage({ params }: PageProps<"/[lang]/jobs/[jobId]">) {
  const { lang, jobId } = await params;
  const { locale, page } = await load(lang, jobId);
  const t = await getTranslations({ locale, namespace: "job" });
  const { job } = page;
  const meta = [
    job.location,
    job.minimumExperienceYears === null
      ? null
      : t("experience", { years: job.minimumExperienceYears }),
  ].filter((part): part is string => Boolean(part));

  return (
    <div className={styles.page}>
      <nav aria-label={t("breadcrumb")}>
        <Link href="/jobs" className={styles.back}>
          {t("back")}
        </Link>
      </nav>
      <header className={styles.header}>
        <h1 className={styles.title}>{job.title}</h1>
        {meta.length > 0 && (
          <p className={styles.meta}>
            {meta.map((part, index) => (
              <span key={part}>
                {index > 0 ? " · " : null}
                <bdi>{part}</bdi>
              </span>
            ))}
          </p>
        )}
      </header>
      <JobScreen
        jobId={job.id}
        jobTitle={job.title}
        entries={rankJob(page.candidates, page.files)}
      />
    </div>
  );
}
