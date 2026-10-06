import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { Icon } from "../icon/icon";
import styles from "./corrected-field.module.css";

/** Text set apart in its own direction (Unicode first-strong isolate), for use inside a string, so
 *  an email or a date keeps its order inside Arabic text. */
export const isolated = (text: string) => `\u2068${text}\u2069`;

export interface CorrectionNote {
  /** What extraction read, one line per entry; empty when it read nothing. */
  extracted: string[];
  /** Who corrected it, as the interface names a member. */
  by: string;
  /** When, already formatted for the reader. */
  when: string;
}

/**
 * A profile value, marked when a person corrected it (T083, FR-010). A corrected value is never
 * shown as if the machine had read it: it carries the word "Corrected" with its icon, who
 * corrected it and when, and what extraction read before.
 */
export function CorrectedField({
  correction,
  children,
}: {
  correction?: CorrectionNote | undefined;
  children: ReactNode;
}) {
  const t = useTranslations("corrected");
  if (correction === undefined) return <>{children}</>;
  return (
    <div className={styles.corrected}>
      <div className={styles.value}>{children}</div>
      <p className={styles.note}>
        <span className={styles.tag}>
          <Icon name="check" size={12} strokeWidth={2.25} />
          {t("corrected")}
        </span>
        <span>
          {t("byWhom", { name: isolated(correction.by), when: isolated(correction.when) })}
        </span>
      </p>
      <p className={styles.extracted}>
        {correction.extracted.length === 0
          ? t("extractedNothing")
          : t("extracted", { value: isolated(correction.extracted.join("; ")) })}
      </p>
    </div>
  );
}
