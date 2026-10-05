"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { AdvisoryNotice } from "@/components/advisory-notice/advisory-notice";
import { Button } from "@/components/button/button";
import { RejectCandidate } from "@/components/reject-candidate/reject-candidate";
import { Decision } from "@/components/status/status";
import type { RejectionReason } from "@/lib/domain/decisions";
import type { Decision as DecisionKind } from "@/lib/domain/ranking";

import styles from "./candidate.module.css";

export interface DecisionState {
  applicationId: string;
  kind: DecisionKind;
  by: string | null;
  /** When, already formatted for the reader. */
  at: string | null;
}

/** Records a decision through the API; the page re-reads itself once it is recorded. */
function useDecide(applicationId: string) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);
  const decide = async (decision: DecisionKind, reason?: RejectionReason): Promise<boolean> => {
    setPending(true);
    setFailed(false);
    try {
      const response = await fetch(`/api/applications/${applicationId}/decision`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ decision, ...(reason !== undefined && { reason }) }),
      });
      if (!response.ok) {
        setFailed(true);
        return false;
      }
      router.refresh();
      return true;
    } catch {
      setFailed(true);
      return false;
    } finally {
      setPending(false);
    }
  };
  return { decide, pending, failed };
}

/** Shortlisting, in the candidate's header where the design puts it (FR-023). */
export function ShortlistButton({ decision }: { decision: DecisionState }) {
  const t = useTranslations("candidate");
  const { decide, pending, failed } = useDecide(decision.applicationId);
  if (decision.kind === "rejected") return null;
  const shortlisted = decision.kind === "shortlisted";
  return (
    <div className={styles.shortlist}>
      <Button
        variant={shortlisted ? "secondary" : "primary"}
        loading={pending}
        onClick={() => {
          void decide(shortlisted ? "undecided" : "shortlisted");
        }}
      >
        {shortlisted ? t("removeShortlist") : t("shortlist")}
      </Button>
      {failed && (
        <p role="alert" className={styles.failed}>
          {t("decisionFailed")}
        </p>
      )}
    </div>
  );
}

/**
 * The decision at the foot of the reasons (T091, T092): who decided and when, the standing line
 * that the score is advice, and the rejection control, which lives only here.
 */
export function DecisionSection({
  decision,
  candidate,
  actor,
}: {
  decision: DecisionState;
  candidate: string;
  actor: string;
}) {
  const t = useTranslations("candidate");
  const { decide, pending, failed } = useDecide(decision.applicationId);
  const decided = decision.kind !== "undecided";
  return (
    <section className={styles.decision}>
      <h2 className={styles.blockTitle}>{t("decision")}</h2>
      {decided && (
        <Decision
          kind={decision.kind}
          {...(decision.by !== null && { by: decision.by })}
          {...(decision.at !== null && { when: decision.at })}
        />
      )}
      <AdvisoryNotice decided={decided} />
      <div className={styles.decisionActions}>
        {decision.kind === "rejected" ? (
          <Button
            variant="secondary"
            loading={pending}
            onClick={() => {
              void decide("undecided");
            }}
          >
            {t("undoRejection")}
          </Button>
        ) : (
          <RejectCandidate
            candidate={candidate}
            actor={actor}
            onReject={(reason) => decide("rejected", reason)}
          />
        )}
      </div>
      {failed && (
        <p role="alert" className={styles.failed}>
          {t("decisionFailed")}
        </p>
      )}
    </section>
  );
}
