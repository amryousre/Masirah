"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { ScoreBreakdown } from "@/components/score/score";
import { Tabs } from "@/components/tabs/tabs";
import type { ProfileRow, ScorePart } from "@/lib/domain/candidate";

import styles from "./candidate.module.css";

interface CandidateScreenProps {
  rank: number | null;
  score: {
    total: number;
    justification: string;
    summary: string[];
    /** Null when the stored components could not be read. */
    parts: ScorePart[] | null;
  } | null;
  /** Null until the CV has been read. */
  profile: ProfileRow[] | null;
  document: { fileName: string; mimeType: string; url: string | null } | null;
}

/**
 * Two panes, reasoning and document (T066). The reasoning sits at the inline start, where the
 * reading eye begins: on the right in Arabic, on the left in English. The justification leads and
 * the breakdown supports it below; the extracted profile is the second tab.
 */
export function CandidateScreen({ rank, score, profile, document }: CandidateScreenProps) {
  const t = useTranslations("candidate");
  const [tab, setTab] = useState("reasons");

  return (
    <div className={styles.panes}>
      <section className={styles.reasoning} aria-label={t("reasons")}>
        <Tabs
          label={t("sections")}
          items={[
            { id: "reasons", label: t("reasons") },
            { id: "profile", label: t("profile") },
          ]}
          selected={tab}
          onSelect={setTab}
        >
          {tab === "reasons" ? <Reasons rank={rank} score={score} /> : <Profile rows={profile} />}
        </Tabs>
      </section>
      <DocumentPane document={document} />
    </div>
  );
}

function Reasons({ rank, score }: Pick<CandidateScreenProps, "rank" | "score">) {
  const t = useTranslations("candidate");
  if (score === null) {
    return (
      <div className={styles.reasons}>
        <p className={styles.quiet}>{t("pending")}</p>
        <ScoreBreakdown state="calculating" />
      </div>
    );
  }
  return (
    <div className={styles.reasons}>
      <section className={styles.block}>
        <h2 className={styles.blockTitle}>
          {rank === null ? t("whyUnranked") : t("why", { rank })}
        </h2>
        <p className={styles.justification}>{score.justification}</p>
      </section>
      {score.summary.length > 0 && (
        <section className={styles.block}>
          <h2 className={styles.blockTitle}>{t("summary")}</h2>
          <ul className={styles.summary}>
            {score.summary.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </section>
      )}
      {score.parts === null ? (
        <ScoreBreakdown state="unavailable" reason={t("breakdownUnavailable")} />
      ) : (
        <ScoreBreakdown total={score.total} parts={score.parts} />
      )}
    </div>
  );
}

function Profile({ rows }: { rows: ProfileRow[] | null }) {
  const t = useTranslations("candidate");
  if (rows === null) return <p className={styles.quiet}>{t("profilePending")}</p>;
  return (
    <dl className={styles.profile}>
      {rows.map((row) => (
        <div key={row.field} className={styles.profileRow}>
          <dt className={styles.profileLabel}>{t(`fields.${row.field}`)}</dt>
          <dd className={styles.profileValue}>
            {row.values.length === 0 ? (
              <span className={styles.quiet}>{t("notGiven")}</span>
            ) : (
              row.values.map((value) => (
                <bdi key={value} className={styles.profileLine}>
                  {row.field === "experience"
                    ? t("experienceYears", { years: Number(value) })
                    : value}
                </bdi>
              ))
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}

const SHOWN_INLINE = new Set(["application/pdf", "image/jpeg", "image/png"]);

/** The retained original beside the reasoning (T067, FR-012). */
function DocumentPane({ document }: Pick<CandidateScreenProps, "document">) {
  const t = useTranslations("candidate");
  return (
    <section className={styles.document} aria-label={t("document")}>
      {document === null ? (
        <p className={styles.quiet}>{t("noDocument")}</p>
      ) : (
        <>
          <div className={styles.documentBar}>
            <bdi className={styles.fileName}>{document.fileName}</bdi>
            {document.url !== null && (
              <a href={document.url} target="_blank" rel="noreferrer" className={styles.link}>
                {t("openOriginal")}
              </a>
            )}
          </div>
          {document.url === null || !SHOWN_INLINE.has(document.mimeType) ? (
            <p className={styles.quiet}>{t("noPreview")}</p>
          ) : document.mimeType === "application/pdf" ? (
            // The browser's own viewer, opened at page width without its thumbnail rail.
            <iframe
              src={`${document.url}#view=FitH&navpanes=0`}
              title={document.fileName}
              className={styles.viewer}
            />
          ) : (
            // A signed Storage URL, not a Next image: it must not be cached or optimised.
            // eslint-disable-next-line @next/next/no-img-element
            <img src={document.url} alt={document.fileName} className={styles.image} />
          )}
        </>
      )}
    </section>
  );
}
