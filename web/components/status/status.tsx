import { useTranslations } from "next-intl";

import { Icon, type IconName } from "../icon/icon";
import styles from "./status.module.css";

// Every indicator is a shape and a word; hue is a third, redundant channel (DESIGN.md section 3).

type Tone = "muted" | "success" | "warning" | "error";

export type DocumentStatusKind =
  "queued" | "processing" | "parsed" | "needsReview" | "failed" | "unsupportedLanguage";

const documentLook: Record<DocumentStatusKind, { icon: IconName; tone: Tone }> = {
  queued: { icon: "queued", tone: "muted" },
  processing: { icon: "spinner", tone: "muted" },
  parsed: { icon: "checkCircle", tone: "success" },
  needsReview: { icon: "alert", tone: "warning" },
  failed: { icon: "xCircle", tone: "error" },
  unsupportedLanguage: { icon: "globeOff", tone: "muted" },
};

/** Where a CV is: nothing is ever silently lost, so every state has a name. */
export function DocumentStatus({ status }: { status: DocumentStatusKind }) {
  const t = useTranslations("status.document");
  const { icon, tone } = documentLook[status];
  return (
    <span className={styles.status} data-tone={tone}>
      <Icon name={icon} size={14} />
      <span>{t(status)}</span>
    </span>
  );
}

export type ConfidenceLevel = "high" | "medium" | "low";

const steps: Record<ConfidenceLevel, number> = { high: 3, medium: 2, low: 1 };

/** A three-step meter with a word. Low confidence can also ask for review in words. */
export function Confidence({
  level,
  showHint = false,
}: {
  level: ConfidenceLevel;
  showHint?: boolean;
}) {
  const t = useTranslations("status.confidence");
  return (
    <span className={styles.confidence} data-level={level}>
      <span className={styles.meter} aria-hidden="true">
        {[1, 2, 3].map((step) => (
          <span
            key={step}
            className={styles.step}
            data-step={step <= steps[level] ? "on" : "off"}
          />
        ))}
      </span>
      <span>{t(level)}</span>
      {showHint && level === "low" && <span className={styles.hint}>{t("lowHint")}</span>}
    </span>
  );
}

export type DecisionKind = "undecided" | "shortlisted" | "rejected";

const decisionIcon: Record<DecisionKind, IconName> = {
  undecided: "dot",
  shortlisted: "check",
  rejected: "minusCircle",
};

interface DecisionProps {
  kind: DecisionKind;
  /** Who decided. A decision is never shown without its person (FR-023 in the Phase 1 spec). */
  by?: string;
  when?: string;
  /** Adds the second line under an undecided candidate: "No decision yet". */
  detailed?: boolean;
  /** One line, for a table row: "Rejected · Nourhan". */
  compact?: boolean;
}

export function Decision({ kind, by, when, detailed = false, compact = false }: DecisionProps) {
  const t = useTranslations("status.decision");
  if (compact) {
    return (
      <span className={styles.status} data-kind={kind}>
        <Icon name={decisionIcon[kind]} size={14} />
        <span>{by === undefined ? t(kind) : t("compact", { decision: t(kind), name: by })}</span>
      </span>
    );
  }
  const detail =
    by !== undefined && when !== undefined
      ? t("byWhom", { name: by, when })
      : kind === "undecided" && detailed
        ? t("undecidedDetail")
        : undefined;
  return (
    <span className={styles.decision} data-kind={kind}>
      <span className={styles.status}>
        <Icon name={decisionIcon[kind]} size={14} />
        <span>{t(kind)}</span>
      </span>
      {detail !== undefined && <span className={styles.detail}>{detail}</span>}
    </span>
  );
}
