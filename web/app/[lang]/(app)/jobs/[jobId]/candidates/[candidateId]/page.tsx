import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";

import { Icon } from "@/components/icon/icon";
import { Decision } from "@/components/status/status";
import { Link } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { recordActivity } from "@/lib/adapters/activity";
import { readCandidatePage } from "@/lib/adapters/candidate-page";
import { getAccess } from "@/lib/adapters/session";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";
import { memberNames } from "@/lib/adapters/corrections";
import { placeInRanking, scoreParts, summaryLines } from "@/lib/domain/candidate";
import { correctedRows, correctionsOf } from "@/lib/domain/corrections";
import { confidenceLevel, rankJob } from "@/lib/domain/ranking";

import { CandidateScreen } from "./candidate-screen";
import { type DecisionState, ShortlistButton } from "./decision-controls";
import type { PrivacyState } from "./personal-data";
import styles from "./candidate.module.css";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
/** Long enough to read the document, short enough that a copied link soon stops working. */
const DOCUMENT_LINK_SECONDS = 600;
/** Decisions are read in Egypt's time, whoever renders the page. */
const TIME_ZONE = "Africa/Cairo";

async function load(lang: string, jobId: string, candidateId: string) {
  if (!hasLocale(routing.locales, lang) || !UUID.test(jobId) || !UUID.test(candidateId)) {
    notFound();
  }
  const supabase = await createSupabaseServerClient();
  const page = await readCandidatePage(supabase, jobId, candidateId);
  // Another organisation's candidate, or one who never applied to this job, is simply not found.
  if (page === null) notFound();
  return { locale: lang, page, supabase };
}

export async function generateMetadata({
  params,
}: PageProps<"/[lang]/jobs/[jobId]/candidates/[candidateId]">): Promise<Metadata> {
  const { lang, jobId, candidateId } = await params;
  const { locale, page } = await load(lang, jobId, candidateId);
  const t = await getTranslations({ locale, namespace: "job" });
  return { title: page.candidate.name ?? t("unnamed") };
}

// A candidate's own page (T066): the written reasons lead and the score follows them; the
// original document sits beside them so every claim can be checked against it (FR-012, FR-015).
export default async function CandidatePage({
  params,
}: PageProps<"/[lang]/jobs/[jobId]/candidates/[candidateId]">) {
  const { lang, jobId, candidateId } = await params;
  const { locale, page, supabase } = await load(lang, jobId, candidateId);
  const t = await getTranslations({ locale, namespace: "candidate" });
  const tJob = await getTranslations({ locale, namespace: "job" });

  const ranked = rankJob(page.ranking.candidates, page.ranking.files).flatMap((entry) =>
    entry.kind === "ranked" ? [entry] : [],
  );
  const place = placeInRanking(ranked, candidateId);
  const confidence = page.profile === null ? null : confidenceLevel(page.profile.confidence);
  const meta = [
    place === null ? null : t("rank", { rank: place.rank, of: place.of }),
    page.score === null ? t("notScored") : t("score", { total: page.score.total }),
    confidence === null ? null : t(`confidence.${confidence}`),
  ].filter((part): part is string => part !== null);

  const access = await getAccess();
  // Every view of a candidate is on the audit trail (T099, FR-074), before anything is shown.
  if (access.kind === "member") {
    await recordActivity(
      supabase,
      access.session,
      "candidate.viewed",
      { type: "candidate", id: candidateId },
      { job_id: jobId },
    );
  }
  const actor = access.kind === "member" ? (access.session.name ?? access.session.email) : "";
  const decision: DecisionState = {
    applicationId: page.decision.applicationId,
    kind: page.decision.kind,
    by: page.decision.by,
    at:
      page.decision.at === null
        ? null
        : new Intl.DateTimeFormat(locale, {
            dateStyle: "medium",
            timeStyle: "short",
            timeZone: TIME_ZONE,
          }).format(new Date(page.decision.at)),
  };

  const when = (at: string | null) =>
    at === null
      ? null
      : new Intl.DateTimeFormat(locale, {
          dateStyle: "medium",
          timeStyle: "short",
          timeZone: TIME_ZONE,
        }).format(new Date(at));
  const privacy: PrivacyState = {
    candidateId,
    purgedAt: when(page.privacy.purgedAt),
    requestedAt: when(page.privacy.requestedAt),
  };

  // The profile as corrected, each corrected row naming who corrected it and when (T083).
  const corrections = correctionsOf(page.profile?.corrections);
  const names = await memberNames(
    supabase,
    Object.values(corrections).map((correction) => correction.by),
  );
  const profile =
    page.profile === null
      ? null
      : (correctedRows(page.profile.values, corrections) ?? []).map(({ corrected, ...row }) =>
          corrected === undefined
            ? row
            : {
                ...row,
                corrected: {
                  extracted: corrected.extracted,
                  by: names.get(corrected.by) ?? "",
                  when: when(corrected.at) ?? "",
                },
              },
        );

  let documentUrl: string | null = null;
  if (page.document !== null) {
    const { data } = await supabase.storage
      .from("cv-originals")
      .createSignedUrl(page.document.storagePath, DOCUMENT_LINK_SECONDS);
    documentUrl = data?.signedUrl ?? null;
  }

  const neighbour = (id: string | null, label: string, icon: "chevronRight" | "chevronLeft") =>
    id === null ? (
      <span className={styles.step} aria-disabled="true" title={label}>
        <Icon name={icon} label={label} className={styles.chevron} />
      </span>
    ) : (
      <Link href={`/jobs/${jobId}/candidates/${id}`} className={styles.step} title={label}>
        <Icon name={icon} label={label} className={styles.chevron} />
      </Link>
    );

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.heading}>
          <nav aria-label={t("breadcrumb")}>
            <Link href={`/jobs/${jobId}`} className={styles.back}>
              {t("back")}
            </Link>
          </nav>
          <h1 className={styles.title}>{page.candidate.name ?? tJob("unnamed")}</h1>
          <p className={styles.meta}>
            <span>{meta.join(" · ")}</span>
            <Decision
              kind={page.decision.kind}
              compact
              {...(page.decision.by !== null && { by: page.decision.by })}
            />
          </p>
        </div>
        <div className={styles.headerActions}>
          <ShortlistButton decision={decision} />
          {place !== null && (
            <nav aria-label={t("navigation")} className={styles.steps}>
              {neighbour(place.previous, t("previous"), "chevronLeft")}
              {neighbour(place.next, t("next"), "chevronRight")}
            </nav>
          )}
        </div>
      </header>
      <CandidateScreen
        candidate={page.candidate.name ?? tJob("unnamed")}
        actor={actor}
        decision={decision}
        privacy={privacy}
        rank={place?.rank ?? null}
        score={
          page.score === null
            ? null
            : {
                total: page.score.total,
                justification: page.score.justification,
                summary: summaryLines(page.score.summary),
                parts: scoreParts(page.score.components, page.job.weights),
              }
        }
        profile={profile}
        correctHref={
          page.document === null || page.profile === null || page.privacy.purgedAt !== null
            ? null
            : {
                pathname: `/candidates/${candidateId}/edit`,
                query: { file: page.document.id, job: jobId },
              }
        }
        document={
          page.document === null
            ? null
            : {
                fileName: page.document.fileName,
                mimeType: page.document.mimeType,
                url: documentUrl,
                downloadHref: `/api/candidates/${candidateId}/original?job=${jobId}`,
              }
        }
      />
    </div>
  );
}
