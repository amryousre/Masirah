import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getFormatter, getTranslations } from "next-intl/server";

import { Icon } from "@/components/icon/icon";
import { DocumentStatus } from "@/components/status/status";
import { Link } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { recordActivity } from "@/lib/adapters/activity";
import { listReviewQueue, reviewOriginal } from "@/lib/adapters/review-queue";
import { getAccess } from "@/lib/adapters/session";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";
import type { ReviewItem } from "@/lib/domain/review-queue";

import styles from "./review.module.css";

/** Long enough to read the original, short enough not to pass the link on. */
const PREVIEW_SECONDS = 600;
const SHOWN_INLINE = new Set(["application/pdf", "image/jpeg", "image/png"]);

export async function generateMetadata({ params }: PageProps<"/[lang]/review">): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "review" });
  return { title: t("title") };
}

// The review queue (T081, FR-011): every CV that was not ranked, each with its reason in plain
// words, what helps, and its original beside it. A file is chosen by ?file=; without one the
// first is shown on a wide screen, and a phone shows the list until a file is chosen.
export default async function ReviewPage({ params, searchParams }: PageProps<"/[lang]/review">) {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "review" });
  const access = await getAccess();
  if (access.kind !== "member") return null;
  const supabase = await createSupabaseServerClient();
  const items = await listReviewQueue(supabase);

  const [first] = items;
  if (first === undefined) {
    return (
      <div className={styles.page}>
        <h1 className={styles.title}>{t("title")}</h1>
        <section className={styles.empty} aria-labelledby="review-empty">
          <h2 id="review-empty" className={styles.emptyTitle}>
            {t("empty.title")}
          </h2>
          <p className={styles.emptyBody}>{t("empty.body")}</p>
        </section>
      </div>
    );
  }

  const { file } = await searchParams;
  const chosen = typeof file === "string" ? items.find((item) => item.id === file) : undefined;
  const selected = chosen ?? first;

  let previewUrl: string | null = null;
  if (SHOWN_INLINE.has(selected.mimeType)) {
    const original = await reviewOriginal(supabase, selected.id);
    if (original !== null) {
      const { data } = await supabase.storage
        .from("cv-originals")
        .createSignedUrl(original.storagePath, PREVIEW_SECONDS);
      previewUrl = data?.signedUrl ?? null;
    }
  }
  // A CV shown is a CV viewed: on the audit trail before it is shown (T099, FR-074).
  if (previewUrl !== null) {
    await recordActivity(supabase, access.session, "cv_file.viewed", {
      type: "cv_file",
      id: selected.id,
    });
  }

  const format = await getFormatter({ locale: lang });
  const now = new Date();
  const languages = new Intl.DisplayNames([lang], { type: "language" });
  const short = (item: ReviewItem) =>
    t(`kind.${item.kind}.short`, {
      language: item.language === null ? "" : (languages.of(item.language) ?? item.language),
    });
  const placed = (item: ReviewItem) =>
    `${item.jobTitle ?? t("noJob")} · ${format.relativeTime(new Date(item.updatedAt), now)}`;

  return (
    <div className={styles.page} data-chosen={chosen === undefined ? undefined : true}>
      <header className={styles.header}>
        <h1 className={styles.title}>{t("title")}</h1>
        <p className={styles.summary}>{t("summary", { count: items.length })}</p>
      </header>

      <div className={styles.queue}>
        <nav aria-label={t("list")} className={styles.list}>
          <ul>
            {items.map((item) => (
              <li key={item.id}>
                <Link
                  href={{ pathname: "/review", query: { file: item.id } }}
                  className={styles.item}
                  aria-current={item.id === selected.id ? "true" : undefined}
                >
                  <bdi className={styles.fileName}>{item.fileName}</bdi>
                  <DocumentStatus status={item.status} />
                  <span className={styles.reason}>{short(item)}</span>
                  <span className={styles.placed}>{placed(item)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <section className={styles.detail} aria-labelledby="review-file">
          <div className={styles.info}>
            <Link href="/review" className={styles.back}>
              <Icon name={lang === "ar" ? "chevronRight" : "chevronLeft"} size={16} />
              {t("back")}
            </Link>
            <div className={styles.heading}>
              <h2 id="review-file" className={styles.detailName}>
                <bdi>{selected.fileName}</bdi>
              </h2>
              <p className={styles.placed}>{placed(selected)}</p>
            </div>
            <div className={styles.callout} data-status={selected.status}>
              <DocumentStatus status={selected.status} />
              <p className={styles.calloutText}>{short(selected)}</p>
            </div>
            <p className={styles.body}>{t(`kind.${selected.kind}.detail`)}</p>
            <div className={styles.helps}>
              <h3 className={styles.helpsTitle}>{t("whatHelps")}</h3>
              <p className={styles.body}>{t(`kind.${selected.kind}.action`)}</p>
            </div>
            <div className={styles.actions}>
              <a href={`/api/cv-files/${selected.id}/original`} className={styles.action}>
                {t("download")}
              </a>
              {selected.jobId !== null && selected.jobTitle !== null && (
                <Link href={`/jobs/${selected.jobId}`} className={styles.action}>
                  {t("openJob", { job: selected.jobTitle })}
                </Link>
              )}
            </div>
          </div>

          <figure className={styles.original} aria-label={t("original")}>
            {previewUrl === null ? (
              <p className={styles.noPreview}>{t("noPreview")}</p>
            ) : selected.mimeType === "application/pdf" ? (
              // The browser's own viewer, opened at page width without its thumbnail rail.
              <iframe
                src={`${previewUrl}#view=FitH&navpanes=0`}
                title={selected.fileName}
                className={styles.viewer}
              />
            ) : (
              // A signed Storage URL, not a Next image: it must not be cached or optimised.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={previewUrl} alt={selected.fileName} className={styles.image} />
            )}
          </figure>
        </section>
      </div>
    </div>
  );
}
