"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { DeleteCandidateData } from "@/components/delete-candidate-data/delete-candidate-data";

import styles from "./candidate.module.css";

export interface PrivacyState {
  candidateId: string;
  /** When the purge removed the data, already formatted for the reader. */
  purgedAt: string | null;
  /** When an open removal request was made, already formatted. */
  requestedAt: string | null;
}

/**
 * Deleting a candidate's personal data on request, from their own page (T101, FR-076). Once asked,
 * the section says the deletion is waiting, and once the worker has run, that it is done.
 */
export function PersonalData({ privacy, candidate }: { privacy: PrivacyState; candidate: string }) {
  const t = useTranslations("privacy");
  const router = useRouter();
  const [failed, setFailed] = useState(false);

  const remove = async (): Promise<boolean> => {
    setFailed(false);
    try {
      const response = await fetch(`/api/candidates/${privacy.candidateId}`, { method: "DELETE" });
      if (!response.ok) {
        setFailed(true);
        return false;
      }
      router.refresh();
      return true;
    } catch {
      setFailed(true);
      return false;
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
          <DeleteCandidateData
            candidate={candidate}
            onDelete={remove}
            error={failed ? t("failed") : undefined}
          />
        </>
      )}
    </section>
  );
}
