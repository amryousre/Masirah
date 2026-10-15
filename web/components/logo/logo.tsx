import { useTranslations } from "next-intl";

import styles from "./logo.module.css";

/**
 * The Masirah logo (DESIGN.md section 3): the M-tick mark from the Canva logo, an M whose tick
 * rises out of its valley, beside the product's name in the page's language. The mark is drawn, so
 * it stays sharp at header size, and takes its colours from the tokens: the M in amber-400, the
 * identity anchor, and the tick a shade darker, as in the logo.
 */
export function Logo() {
  const product = useTranslations("meta")("product");
  return (
    <span className={styles.logo}>
      <svg viewBox="4 3 28 26" className={styles.mark} aria-hidden="true" focusable="false">
        <g className={styles.legs}>
          <path d="M5.5 26.5V8h4.4l3.2 4.4v14.1z" fill="currentColor" />
          <path d="M21 13h4.6v13.5H21z" fill="currentColor" />
        </g>
        <path
          className={styles.tick}
          d="M10.2 13.2 16 21.4 27.4 4.4l2.9 2.1L16.1 27.2 7.4 15.2z"
          fill="currentColor"
        />
      </svg>
      <span className={styles.name}>{product}</span>
    </span>
  );
}
