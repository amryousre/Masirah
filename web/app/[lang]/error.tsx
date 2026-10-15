"use client";

import { captureException } from "@sentry/nextjs";
import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { Button } from "@/components/button/button";

import styles from "./not-found.module.css";

/**
 * What a page shows when it fails to render (T031). The error is reported to Sentry from here:
 * a render error caught by this boundary never reaches the browser SDK's own handlers. Server
 * render errors are also reported by onRequestError (instrumentation.ts); Sentry groups the two.
 */
export default function PageError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  const t = useTranslations("pageError");
  useEffect(() => {
    captureException(error);
  }, [error]);
  return (
    <main className={styles.page}>
      <h1 className={styles.title}>{t("title")}</h1>
      <p className={styles.body}>{t("body")}</p>
      <Button
        variant="primary"
        onClick={() => {
          retry();
        }}
      >
        {t("retry")}
      </Button>
    </main>
  );
}
