"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { REJECTION_REASONS, type RejectionReason } from "@/lib/domain/decisions";

import { Button } from "../button/button";
import { RejectDialog } from "../reject-dialog/reject-dialog";

interface RejectCandidateProps {
  candidate: string;
  /** The signed-in member, who will be recorded as deciding. */
  actor: string;
  /** Records the rejection; true once it is recorded. */
  onReject: (reason: RejectionReason) => Promise<boolean>;
}

/**
 * The one place a candidate is rejected (T092, FR-023). It lives in the candidate's decision
 * section, never in a list row where a hover could put it under the pointer. It opens a
 * confirmation that states the consequence and needs a reason; nothing is recorded before then.
 */
export function RejectCandidate({ candidate, actor, onReject }: RejectCandidateProps) {
  const t = useTranslations("reject");
  const locale = useLocale();
  const [open, setOpen] = useState(false);
  const [recording, setRecording] = useState(false);
  const [when, setWhen] = useState("");

  return (
    <>
      <Button
        variant="destructive"
        onClick={() => {
          setWhen(
            new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(
              new Date(),
            ),
          );
          setOpen(true);
        }}
      >
        {t("open")}
      </Button>
      <RejectDialog
        open={open}
        candidate={candidate}
        actor={actor}
        when={when}
        reasons={REJECTION_REASONS.map((reason) => ({
          value: reason,
          label: t(`reasons.${reason}`),
        }))}
        offerNotice={false}
        recording={recording}
        onCancel={() => {
          setOpen(false);
        }}
        onConfirm={({ reason }) => {
          const chosen = REJECTION_REASONS.find((known) => known === reason);
          if (chosen === undefined) return;
          setRecording(true);
          void onReject(chosen).then((recorded) => {
            setRecording(false);
            if (recorded) setOpen(false);
          });
        }}
      />
    </>
  );
}
