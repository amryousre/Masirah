import type { Locale } from "next-intl";
import { getFormatter, getTranslations } from "next-intl/server";

import { attention, type JobSummary, rankedShare } from "@/lib/domain/jobs";

import styles from "./job-table.module.css";

// Recruiters are in Egypt; "today" and "yesterday" are Cairo's, whatever the server's zone.
const TIME_ZONE = "Africa/Cairo";

interface JobTableProps {
  jobs: readonly JobSummary[];
  locale: Locale;
  /** The moment the page was rendered, so every row is dated against the same "now". */
  now: Date;
}

/**
 * The job list (T058): one row per job. Rows, not cards, as with candidates: a recruiter scans
 * down the progress and "needs you" columns.
 */
export async function JobTable({ jobs, locale, now }: JobTableProps) {
  const t = await getTranslations({ locale, namespace: "jobs" });
  const format = await getFormatter({ locale });

  // A job's place and experience, each in its own direction: an English place name beside
  // "3+ سنوات" would otherwise be reordered by the surrounding Arabic.
  const meta = (job: JobSummary) =>
    [
      job.location,
      job.minimumExperienceYears === null
        ? null
        : t("experience", { years: job.minimumExperienceYears }),
    ].filter((part): part is string => Boolean(part));

  const needs = (job: JobSummary) => {
    const need = attention(job);
    switch (need.kind) {
      case "no-cvs":
        return t("attention.noCvs");
      case "processing":
        return t("attention.processing", {
          processing: need.processing,
          decisions: need.decisions,
        });
      case "decisions":
        return t("attention.decisions", { decisions: need.decisions });
      case "nothing":
        return t("attention.nothing");
    }
  };

  const day = (date: Date) =>
    format.dateTime(date, {
      timeZone: TIME_ZONE,
      year: "numeric",
      month: "numeric",
      day: "numeric",
    });
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  const updated = (iso: string) => {
    const at = new Date(iso);
    if (day(at) === day(now)) {
      const time = format.dateTime(at, {
        timeZone: TIME_ZONE,
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23",
      });
      return t("updatedToday", { time });
    }
    if (day(at) === day(yesterday)) return t("updatedYesterday");
    return format.dateTime(at, { timeZone: TIME_ZONE, day: "numeric", month: "short" });
  };

  return (
    <table className={styles.table}>
      <caption className={styles.caption}>{t("caption")}</caption>
      <thead>
        <tr>
          <th scope="col">{t("column.job")}</th>
          <th scope="col" className={styles.number}>
            {t("column.cvs")}
          </th>
          <th scope="col">{t("column.progress")}</th>
          <th scope="col">{t("column.attention")}</th>
          <th scope="col">{t("column.updated")}</th>
        </tr>
      </thead>
      <tbody>
        {jobs.map((job) => {
          const need = attention(job).kind;
          return (
            <tr key={job.id} className={styles.row}>
              <td>
                {/* The job's own page, with its ranked candidates, is T063; the title links there
                    once it exists. */}
                <span className={styles.title}>{job.title}</span>
                {meta(job).length > 0 ? (
                  <span className={styles.meta}>
                    {meta(job).map((part, index) => (
                      <span key={part}>
                        {index > 0 ? " · " : null}
                        <bdi>{part}</bdi>
                      </span>
                    ))}
                  </span>
                ) : null}
              </td>
              <td className={styles.number}>{job.cvCount}</td>
              <td>
                <span className={styles.progressText}>
                  {job.cvCount === 0
                    ? t("noCvs")
                    : t("progress", { ranked: job.rankedCount, total: job.cvCount })}
                </span>
                <span className={styles.track} aria-hidden="true">
                  <span
                    className={styles.fill}
                    style={{ "--fill": `${String(Math.round(rankedShare(job) * 100))}%` }}
                  />
                </span>
              </td>
              <td className={styles.attention} data-need={need}>
                {needs(job)}
              </td>
              <td className={styles.updated}>
                <time dateTime={job.updatedAt}>{updated(job.updatedAt)}</time>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
