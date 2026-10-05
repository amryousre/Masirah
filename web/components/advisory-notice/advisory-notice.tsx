import { useTranslations } from "next-intl";

import styles from "./advisory-notice.module.css";

/**
 * The standing line under every decision (T091, FR-023): the score is advice, the decision is the
 * reader's and is recorded under their name. Said once, in plain text, never as a warning: it
 * stands beside the decision rather than interrupting it.
 */
export function AdvisoryNotice({ decided }: { decided: boolean }) {
  const t = useTranslations("advisory");
  return <p className={styles.notice}>{decided ? t("standing") : t("undecided")}</p>;
}
