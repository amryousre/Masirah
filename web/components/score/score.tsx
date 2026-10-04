import { useTranslations } from "next-intl";

import { Icon } from "../icon/icon";
import styles from "./score.module.css";

// A score is a numeral and a neutral bar, never a color grade, and it always follows the
// reasoning rather than leading it (DESIGN.md sections 3 and 7).

/** The score in a candidate row: 13px numeral, grey bar filled to the score. */
export function ScoreBar({ value }: { value: number }) {
  return (
    <span className={styles.scoreBar}>
      <span className={styles.value}>{value}</span>
      <span
        data-bar
        aria-hidden="true"
        className={styles.track}
        style={{ "--fill": `${String(value)}%` }}
      >
        <span className={styles.fill} />
      </span>
    </span>
  );
}

export type ScoreComponentKey =
  "skills" | "experience" | "education" | "tenure" | "language" | "location";

export interface ScorePart {
  key: ScoreComponentKey;
  earned: number;
  weight: number;
  /** What the rating rests on, shown under its track. */
  evidence?: string;
}

type ScoreBreakdownProps =
  | { state?: "ready"; total: number; parts: readonly ScorePart[] }
  | { state: "calculating" }
  | { state: "unavailable"; reason: string };

/**
 * Points earned out of each component's weight, on tracks of equal length: a 10-point component
 * reads as "6 of 10", not as a short bar. Bars grow from the inline start, so right to left in
 * Arabic.
 */
export function ScoreBreakdown(props: ScoreBreakdownProps) {
  const t = useTranslations("score");

  if (props.state === "calculating") {
    return (
      <section className={styles.breakdown} aria-busy="true">
        <h3 className={styles.title}>{t("title")}</h3>
        <p className={styles.pending}>
          <Icon name="spinner" size={14} strokeWidth={2.5} />
          {t("calculating")}
        </p>
      </section>
    );
  }

  if (props.state === "unavailable") {
    return (
      <section className={styles.breakdown}>
        <h3 className={styles.title}>{t("unavailable")}</h3>
        <p className={styles.reason}>{props.reason}</p>
      </section>
    );
  }

  return (
    <section className={styles.breakdown}>
      <h3 className={styles.title}>{t("title")}</h3>
      <p className={styles.total}>
        <span className={styles.totalLabel}>{t("total")}</span>
        {/* "78 / 100" runs left to right in both languages: in a right-to-left line the slash
            would otherwise let the two numbers swap places. */}
        <span className={styles.totalValue} dir="ltr">
          {t("outOf", { earned: props.total, max: 100 })}
        </span>
      </p>
      <ul className={styles.parts}>
        {props.parts.map((part) => (
          <li key={part.key} className={styles.part}>
            <span className={styles.partLabel}>
              {t("component", { name: t(part.key), weight: part.weight })}
            </span>
            <span className={styles.partValue} dir="ltr">
              {t("outOf", { earned: part.earned, max: part.weight })}
            </span>
            <span
              data-track
              aria-hidden="true"
              className={styles.partTrack}
              style={{ "--fill": `${String(Math.round((part.earned / part.weight) * 100))}%` }}
            >
              <span className={styles.fill} />
            </span>
            {part.evidence !== undefined && part.evidence !== "" && (
              <span className={styles.partEvidence}>{part.evidence}</span>
            )}
          </li>
        ))}
      </ul>
      <p className={styles.excluded}>{t("excluded")}</p>
    </section>
  );
}
