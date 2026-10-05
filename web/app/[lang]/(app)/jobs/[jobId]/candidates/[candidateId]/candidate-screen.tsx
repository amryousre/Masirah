"use client";

import { useLocale, useTranslations } from "next-intl";
import { type KeyboardEvent, useId, useRef, useState } from "react";

import { cx } from "@/components/cx";
import { ScoreBreakdown } from "@/components/score/score";
import { Tabs } from "@/components/tabs/tabs";
import tabStyles from "@/components/tabs/tabs.module.css";
import { direction } from "@/i18n/routing";
import type { ProfileRow, ScorePart } from "@/lib/domain/candidate";

import styles from "./candidate.module.css";
import { DecisionSection, type DecisionState } from "./decision-controls";

interface CandidateScreenProps {
  candidate: string;
  /** The signed-in member, recorded as deciding. */
  actor: string;
  decision: DecisionState;
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
 * the breakdown supports it below; the extracted profile is the second tab. Below 700 pixels the
 * panes become tabs, reasoning first (T071): stacked, the document would fall below the fold.
 */
export function CandidateScreen({
  candidate,
  actor,
  decision,
  rank,
  score,
  profile,
  document,
}: CandidateScreenProps) {
  const t = useTranslations("candidate");
  const [section, setSection] = useState<Section>("reasons");
  const [documentShown, setDocumentShown] = useState(false);
  const ids = { reasoning: useId(), document: useId() };
  const view: View = documentShown ? "document" : section;

  return (
    <div className={styles.panes}>
      <ViewTabs
        selected={view}
        onSelect={(next) => {
          setDocumentShown(next === "document");
          if (next !== "document") setSection(next);
        }}
        ids={ids}
      />
      <section
        id={ids.reasoning}
        className={styles.reasoning}
        aria-label={t("reasons")}
        data-phone-hidden={documentShown || undefined}
      >
        <Tabs
          label={t("sections")}
          items={[
            { id: "reasons", label: t("reasons") },
            { id: "profile", label: t("profile") },
          ]}
          selected={section}
          onSelect={(next) => {
            setSection(next === "profile" ? "profile" : "reasons");
          }}
        >
          {section === "reasons" ? (
            <>
              <Reasons rank={rank} score={score} />
              <DecisionSection decision={decision} candidate={candidate} actor={actor} />
            </>
          ) : (
            <Profile rows={profile} />
          )}
        </Tabs>
      </section>
      <DocumentPane id={ids.document} document={document} phoneHidden={!documentShown} />
    </div>
  );
}

type Section = "reasons" | "profile";
type View = Section | "document";
const VIEWS: readonly View[] = ["reasons", "profile", "document"];

/**
 * The phone's one row of tabs: the reasoning pane's two sections, then the document. It replaces
 * the pane's own tabs below 700 pixels and is hidden above, so it is never announced on a laptop.
 * Arrow keys follow the reading direction, as in the shared tabs.
 */
function ViewTabs({
  selected,
  onSelect,
  ids,
}: {
  selected: View;
  onSelect: (view: View) => void;
  ids: { reasoning: string; document: string };
}) {
  const t = useTranslations("candidate");
  const rtl = direction(useLocale()) === "rtl";
  const tabs = useRef(new Map<View, HTMLButtonElement>());
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const index = VIEWS.indexOf(selected);
    const step = { ArrowRight: rtl ? -1 : 1, ArrowLeft: rtl ? 1 : -1 }[event.key];
    const next =
      event.key === "Home"
        ? VIEWS[0]
        : event.key === "End"
          ? VIEWS[VIEWS.length - 1]
          : step === undefined
            ? undefined
            : VIEWS[(index + step + VIEWS.length) % VIEWS.length];
    if (next === undefined) return;
    event.preventDefault();
    onSelect(next);
    tabs.current.get(next)?.focus();
  };
  const labels: Record<View, string> = {
    reasons: t("reasons"),
    profile: t("profile"),
    document: t("documentTab"),
  };
  return (
    <div role="tablist" aria-label={t("views")} className={cx(tabStyles.list, styles.viewTabs)}>
      {VIEWS.map((view) => (
        <button
          key={view}
          ref={(node) => {
            if (node) tabs.current.set(view, node);
            else tabs.current.delete(view);
          }}
          type="button"
          role="tab"
          aria-selected={view === selected}
          aria-controls={view === "document" ? ids.document : ids.reasoning}
          tabIndex={view === selected ? 0 : -1}
          className={tabStyles.tab}
          onClick={() => {
            onSelect(view);
          }}
          onKeyDown={onKeyDown}
        >
          {labels[view]}
        </button>
      ))}
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
function DocumentPane({
  id,
  document,
  phoneHidden,
}: Pick<CandidateScreenProps, "document"> & { id: string; phoneHidden: boolean }) {
  const t = useTranslations("candidate");
  return (
    <section
      id={id}
      className={styles.document}
      aria-label={t("document")}
      data-phone-hidden={phoneHidden || undefined}
    >
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
