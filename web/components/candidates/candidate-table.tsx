"use client";

import { useTranslations } from "next-intl";
import { useId } from "react";

import { cx } from "../cx";
import { Icon } from "../icon/icon";
import { ScoreBar } from "../score/score";
import {
  Confidence,
  type ConfidenceLevel,
  Decision,
  type DecisionKind,
  DocumentStatus,
} from "../status/status";
import styles from "./candidate-table.module.css";

export type CandidateRow =
  | {
      kind: "ranked";
      id: string;
      rank: number;
      name: string;
      /** The first line of the justification. */
      reason: string;
      score: number;
      confidence: ConfidenceLevel;
      decision: { kind: DecisionKind; by?: string };
      needsReview?: boolean;
    }
  | { kind: "processing"; id: string; fileName: string }
  /** Read, but too doubtful to rank until someone checks it (FR-011). */
  | { kind: "review"; id: string; fileName: string }
  | { kind: "failed"; id: string; fileName: string; reason: string };

type RankedRow = Extract<CandidateRow, { kind: "ranked" }>;

interface CandidateTableProps {
  rows: readonly CandidateRow[];
  selectedId?: string | undefined;
  onSelect: (id: string) => void;
}

/**
 * The ranked list, modelled on Linear: 36px rows, the reason in the widest column and the score
 * after it. Selection is the only amber. Documents still processing or unreadable sit in a
 * labelled group below the ranking, never hidden (Principle 5).
 */
export function CandidateTable({ rows, selectedId, onSelect }: CandidateTableProps) {
  const t = useTranslations("candidates");
  const unrankedId = useId();
  const ranked = rows.filter((row): row is RankedRow => row.kind === "ranked");
  const unranked = rows.filter((row) => row.kind !== "ranked");

  return (
    <table className={styles.table}>
      <caption className={styles.caption}>{t("caption")}</caption>
      <thead>
        <tr>
          <th scope="col" className={styles.rank}>
            {t("rank")}
          </th>
          <th scope="col">{t("name")}</th>
          <th scope="col" className={styles.reasonHead}>
            {t("reason")}
          </th>
          <th scope="col" aria-sort="descending">
            <span className={styles.sorted}>
              {t("score")}
              <Icon name="sortDown" size={12} />
            </span>
          </th>
          <th scope="col">{t("confidence")}</th>
          <th scope="col">{t("status")}</th>
        </tr>
      </thead>
      <tbody>
        {ranked.map((row) => {
          const selected = row.id === selectedId;
          return (
            <tr
              key={row.id}
              className={styles.row}
              data-selected={selected || undefined}
              data-rejected={row.decision.kind === "rejected" || undefined}
              onClick={() => {
                onSelect(row.id);
              }}
            >
              <td className={styles.rank}>{row.rank}</td>
              <th scope="row" className={styles.name}>
                <button
                  type="button"
                  className={styles.select}
                  aria-current={selected || undefined}
                  onClick={(event) => {
                    event.stopPropagation();
                    onSelect(row.id);
                  }}
                >
                  {row.name}
                </button>
              </th>
              <td className={styles.reason}>{row.reason}</td>
              <td>
                <ScoreBar value={row.score} />
              </td>
              <td>
                <Confidence level={row.confidence} />
              </td>
              <td>
                {row.needsReview ? (
                  <span className={styles.review}>
                    <Icon name="alert" size={14} />
                    {t("lowConfidence")}
                  </span>
                ) : (
                  <Decision
                    kind={row.decision.kind}
                    compact
                    {...(row.decision.by !== undefined && { by: row.decision.by })}
                  />
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
      {unranked.length > 0 && (
        <tbody aria-labelledby={unrankedId}>
          <tr>
            <td id={unrankedId} colSpan={6} className={styles.group}>
              {t("notRanked")}
            </td>
          </tr>
          {unranked.map((row) => (
            <tr key={row.id} className={cx(styles.row, styles.unranked)}>
              <td className={styles.rank} />
              <th scope="row" className={styles.file}>
                {row.fileName}
              </th>
              <td colSpan={4}>
                {row.kind === "processing" ? (
                  <DocumentStatus status="processing" />
                ) : row.kind === "review" ? (
                  <DocumentStatus status="needsReview" />
                ) : (
                  <span className={styles.failed}>
                    <Icon name="xCircle" size={14} />
                    {t("readFailed", { reason: row.reason })}
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      )}
    </table>
  );
}
