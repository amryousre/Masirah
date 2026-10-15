"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { Flip } from "gsap/Flip";
import { useTranslations } from "next-intl";
import { useId, useRef, useState } from "react";

import styles from "./landing.module.css";

gsap.registerPlugin(useGSAP, Flip);

const ROWS = [
  { key: "1", score: 88 },
  { key: "2", score: 84 },
  { key: "3", score: 81 },
  { key: "4", score: 77 },
  { key: "5", score: 70 },
] as const;
type RowKey = (typeof ROWS)[number]["key"];

// The motion tokens' slowest step (globals.css), so the demo keeps to DESIGN.md's 150 to 250 ms.
const SLIDE_SECONDS = 0.2;

/**
 * The ranking as it appears in the product, with illustrative names: choosing a row shows why it
 * ranked there, quoting the CV. The selection slides to the chosen row (GSAP Flip) in the motion
 * tokens' time, and simply moves for a visitor who asked for reduced motion.
 */
export function RankingDemo() {
  const t = useTranslations("landing.demo");
  const [selected, setSelected] = useState<RowKey>("3");
  const root = useRef<HTMLDivElement>(null);
  const before = useRef<Flip.FlipState | null>(null);
  const headingId = useId();

  useGSAP(
    () => {
      const state = before.current;
      before.current = null;
      if (state === null) return;
      Flip.from(state, { duration: SLIDE_SECONDS, ease: "power3.out" });
    },
    { scope: root, dependencies: [selected] },
  );

  // Records where the selection is before it moves; the slide itself is made in useGSAP above,
  // inside its context, so it is cleaned up with the component.
  const choose = (key: RowKey) => {
    if (key === selected) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    before.current = reduced ? null : Flip.getState('[data-flip-id="selection"]');
    setSelected(key);
  };

  return (
    <section aria-labelledby={headingId} className={styles.demoWrap}>
      <div ref={root} className={styles.demo}>
        <header className={styles.demoHead}>
          <h2 id={headingId} className={styles.hidden}>
            {t("name")}
          </h2>
          <p className={styles.demoJob}>{t("job")}</p>
          <p className={styles.demoCounts}>{t("counts")}</p>
        </header>
        <ol className={styles.demoRows}>
          {ROWS.map((row, index) => (
            <li key={row.key}>
              <button
                type="button"
                aria-pressed={row.key === selected}
                className={styles.demoRow}
                onClick={() => {
                  choose(row.key);
                }}
              >
                {row.key === selected && (
                  <span className={styles.selection} data-flip-id="selection" />
                )}
                <span className={styles.demoRank}>{index + 1}</span>
                <span className={styles.demoWho}>
                  <span className={styles.demoName}>{t(`rows.${row.key}.name`)}</span>
                  <span className={styles.demoReason}>{t(`rows.${row.key}.reason`)}</span>
                </span>
                <span className={styles.demoScore}>{row.score}</span>
              </button>
            </li>
          ))}
        </ol>
        <div className={styles.demoWhy} aria-live="polite">
          <h3 className={styles.demoWhyTitle}>{t(`rows.${selected}.why`)}</h3>
          <p className={styles.demoClaim}>{t(`rows.${selected}.claim`)}</p>
          <figure className={styles.demoQuote}>
            <figcaption className={styles.demoSource}>{t("fromCv", { page: 1 })}</figcaption>
            {/* The CV's own words keep their language and direction (DESIGN.md section 4). */}
            <blockquote lang="en" dir="ltr">
              {t(`rows.${selected}.quote`)}
            </blockquote>
          </figure>
        </div>
      </div>
      <p className={styles.demoCaption}>{t("caption")}</p>
    </section>
  );
}
