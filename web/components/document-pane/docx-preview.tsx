"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import styles from "./docx-preview.module.css";

type Preview =
  | { readonly kind: "preparing" }
  | { readonly kind: "ready"; readonly html: string }
  | { readonly kind: "failed" };

/**
 * A Word CV shown as a page beside its extraction (T067, FR-012). The browser cannot display Word,
 * so the file is fetched from its signed link and converted here, in the recruiter's browser, and
 * cleaned before it is shown (docx-html.ts). The converter loads only when a Word CV is opened.
 */
export function DocxPreview({ url, fileName }: { url: string; fileName: string }) {
  const t = useTranslations("candidate");
  const [preview, setPreview] = useState<Preview>({ kind: "preparing" });

  useEffect(() => {
    // Leaving the page, or a new link, abandons the download and its answer.
    const abandoned = new AbortController();
    void (async () => {
      try {
        const response = await fetch(url, { signal: abandoned.signal });
        if (!response.ok) throw new Error(`the original answered ${String(response.status)}`);
        const [{ docxToSafeHtml }, file] = await Promise.all([
          import("./docx-html"),
          response.arrayBuffer(),
        ]);
        const html = await docxToSafeHtml(file);
        if (!abandoned.signal.aborted) setPreview({ kind: "ready", html });
      } catch {
        // The original is still a click away, in the bar above.
        if (!abandoned.signal.aborted) setPreview({ kind: "failed" });
      }
    })();
    return () => {
      abandoned.abort();
    };
  }, [url]);

  if (preview.kind === "preparing") {
    return (
      <p role="status" className={styles.note}>
        {t("preparingPreview")}
      </p>
    );
  }
  if (preview.kind === "failed") {
    return (
      <p role="alert" className={styles.note}>
        {t("previewFailed")}
      </p>
    );
  }
  return (
    <div className={styles.scroller}>
      <article
        className={styles.sheet}
        aria-label={fileName}
        // Cleaned to an allowlist of text structure, tables and embedded pictures (docx-html.ts).
        dangerouslySetInnerHTML={{ __html: preview.html }}
      />
    </div>
  );
}
