"use client";

import { useTranslations } from "next-intl";

import { cx } from "../cx";
import styles from "./evidence.module.css";

// Evidence before verdict: every claim in a justification is numbered and traces to the CV line
// it relied on, or is marked as an absence when the claim is that something is missing.

export type JustificationPart = string | { claim: number; text: string; absence?: boolean };

interface JustificationProps {
  parts: readonly JustificationPart[];
  selected?: number | undefined;
  onSelect: (claim: number) => void;
}

export function Justification({ parts, selected, onSelect }: JustificationProps) {
  return (
    <p className={styles.justification}>
      {parts.map((part, index) =>
        typeof part === "string" ? (
          <span key={index}>{part}</span>
        ) : (
          <button
            key={index}
            type="button"
            className={cx(styles.claim, part.absence && styles.absent)}
            aria-pressed={part.claim === selected}
            onClick={() => {
              onSelect(part.claim);
            }}
          >
            {part.text}
            <span className={styles.number}>{part.claim}</span>
          </button>
        ),
      )}
    </p>
  );
}

export type Quote =
  | { claim: number; kind: "quote"; page: number; section: string; text: string; lang: string }
  | { claim: number; kind: "absence"; searched: readonly string[] }
  | { claim: number; kind: "missing" }
  | { claim: number; kind: "loading" };

interface QuoteListProps {
  quotes: readonly Quote[];
  selected?: number | undefined;
  /** Selecting a quote is how its line gets highlighted in the document beside it. */
  onSelect: (claim: number) => void;
}

export function QuoteList({ quotes, selected, onSelect }: QuoteListProps) {
  const t = useTranslations("evidence");
  return (
    <ol className={styles.quotes}>
      {quotes.map((quote) => {
        const isSelected = quote.claim === selected;
        return (
          <li
            key={quote.claim}
            className={styles.quote}
            data-kind={quote.kind}
            data-selected={isSelected || undefined}
          >
            <div className={styles.quoteHead}>
              <span className={styles.number}>
                {quote.kind === "missing" ? "!" : quote.kind === "loading" ? "…" : quote.claim}
              </span>
              {quote.kind === "quote" && (
                <>
                  <span className={styles.source}>
                    {t("source", { page: quote.page, section: quote.section })}
                  </span>
                  <button
                    type="button"
                    className={styles.show}
                    aria-pressed={isSelected}
                    onClick={() => {
                      onSelect(quote.claim);
                    }}
                  >
                    {t("showInDocument")}
                  </button>
                </>
              )}
              {quote.kind === "absence" && <span className={styles.source}>{t("absence")}</span>}
            </div>
            {quote.kind === "quote" && (
              <q className={styles.text} lang={quote.lang} dir="auto">
                {quote.text}
              </q>
            )}
            {quote.kind === "absence" && (
              <p className={styles.note}>
                {t("searchedFor", { terms: quote.searched.join(t("listSeparator")) })}
              </p>
            )}
            {quote.kind === "missing" && <p className={styles.warning}>{t("notFound")}</p>}
            {quote.kind === "loading" && <p className={styles.note}>{t("loading")}</p>}
          </li>
        );
      })}
    </ol>
  );
}
