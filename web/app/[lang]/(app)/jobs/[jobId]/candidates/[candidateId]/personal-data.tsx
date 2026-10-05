"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/button/button";
import { Dialog } from "@/components/dialog/dialog";

import styles from "./candidate.module.css";

export interface PrivacyState {
  candidateId: string;
  /** When the purge removed the data, already formatted for the reader. */
  purgedAt: string | null;
  /** When an open removal request was made, already formatted. */
  requestedAt: string | null;
}

/**
 * Removing a candidate's personal data on request (T101, FR-076). The confirmation says what goes
 * and what stays before anything is recorded; afterwards the section says a removal is waiting,
 * and once the worker has run, that it is done.
 */
export function PersonalData({ privacy, candidate }: { privacy: PrivacyState; candidate: string }) {
  const t = useTranslations("privacy");
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  const remove = async () => {
    setPending(true);
    setFailed(false);
    try {
      const response = await fetch(`/api/candidates/${privacy.candidateId}`, { method: "DELETE" });
      if (!response.ok) {
        setFailed(true);
        return;
      }
      setOpen(false);
      router.refresh();
    } catch {
      setFailed(true);
    } finally {
      setPending(false);
    }
  };

  return (
    <section className={styles.decision}>
      <h2 className={styles.blockTitle}>{t("title")}</h2>
      {privacy.purgedAt !== null ? (
        <p className={styles.quiet}>{t("removed", { when: privacy.purgedAt })}</p>
      ) : privacy.requestedAt !== null ? (
        <p className={styles.quiet}>{t("requested", { when: privacy.requestedAt })}</p>
      ) : (
        <>
          <p className={styles.quiet}>{t("explain")}</p>
          <Button
            variant="destructive"
            onClick={() => {
              setOpen(true);
            }}
          >
            {t("open")}
          </Button>
        </>
      )}
      <Dialog
        open={open}
        title={t("confirmTitle", { name: candidate })}
        onClose={() => {
          setOpen(false);
        }}
        actions={
          <>
            <Button
              variant="secondary"
              autoFocus
              onClick={() => {
                setOpen(false);
              }}
            >
              {t("keep")}
            </Button>
            <Button
              variant="destructiveConfirm"
              loading={pending}
              loadingLabel={t("recording")}
              onClick={() => {
                void remove();
              }}
            >
              {t("confirm")}
            </Button>
          </>
        }
      >
        <p>{t("consequence")}</p>
        {failed && (
          <p role="alert" className={styles.failed}>
            {t("failed")}
          </p>
        )}
      </Dialog>
    </section>
  );
}
