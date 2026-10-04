import { useTranslations } from "next-intl";

import styles from "./candidate-table.module.css";

/**
 * The break in a ranking where scores fall materially (T064): a row of its own between the last
 * strong candidate and the next, saying how far they fall. Text and a rule, never a colour, so it
 * survives greyscale and reads to a screen reader in table order.
 */
export function DropOffMarker({ gap, columns }: { gap: number; columns: number }) {
  const t = useTranslations("candidates");
  return (
    <tr>
      <td colSpan={columns} className={styles.dropOff}>
        <span>{t("dropOff", { gap })}</span>
      </td>
    </tr>
  );
}
