"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import styles from "./docx-preview.module.css";

type Preview =
  | { readonly kind: "preparing" }
  | { readonly kind: "ready"; readonly html: string }
  | { readonly kind: "failed" };

// Converted CVs, by the file they came from, so a page refresh (which signs a new link) shows the
// page at once rather than downloading and converting the file again. Only the latest few are
// kept: a recruiter moves on through a list of candidates.
const KEPT = 5;
const converted = new Map<string, Promise<string>>();

function convert(key: string, url: string, pictureAlt: string): Promise<string> {
  const known = converted.get(key);
  if (known !== undefined) return known;
  const conversion = (async () => {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`the original answered ${String(response.status)}`);
    const [{ docxToSafeHtml }, file] = await Promise.all([
      import("./docx-html"),
      response.arrayBuffer(),
    ]);
    return docxToSafeHtml(file, { pictureAlt });
  })();
  converted.set(key, conversion);
  // A failure is not kept, so the next visit tries again.
  conversion.catch(() => converted.delete(key));
  for (const old of [...converted.keys()].slice(0, Math.max(0, converted.size - KEPT))) {
    converted.delete(old);
  }
  return conversion;
}

/**
 * A Word CV shown as a page beside its extraction (T067, FR-012). The browser cannot display Word,
 * so the file is fetched from its signed link and converted here, in the recruiter's browser, and
 * cleaned before it is shown (docx-html.ts). The converter loads only when a Word CV is opened.
 * `fileKey` names the file whatever link it is fetched by.
 */
export function DocxPreview({
  url,
  fileKey,
  fileName,
}: {
  url: string;
  fileKey: string;
  fileName: string;
}) {
  const t = useTranslations("candidate");
  const pictureAlt = t("pictureInCv");
  const [result, setResult] = useState<{ key: string; preview: Preview } | null>(null);
  // A different file is preparing until its own result arrives; nothing of the last one shows.
  const preview: Preview = result?.key === fileKey ? result.preview : { kind: "preparing" };

  useEffect(() => {
    let abandoned = false;
    convert(fileKey, url, pictureAlt).then(
      (html) => {
        if (!abandoned) setResult({ key: fileKey, preview: { kind: "ready", html } });
      },
      () => {
        // The original is still a click away, in the bar above.
        if (!abandoned) setResult({ key: fileKey, preview: { kind: "failed" } });
      },
    );
    return () => {
      abandoned = true;
    };
  }, [fileKey, url, pictureAlt]);

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
    // Focusable, so a keyboard can scroll a long CV: its links are made inert, so nothing in it
    // takes focus itself.
    <div className={styles.scroller} tabIndex={0}>
      <article
        className={styles.sheet}
        aria-label={fileName}
        // Cleaned to an allowlist of text structure, tables and embedded pictures (docx-html.ts).
        dangerouslySetInnerHTML={{ __html: preview.html }}
      />
    </div>
  );
}
