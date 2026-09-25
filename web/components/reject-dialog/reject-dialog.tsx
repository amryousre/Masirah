"use client";

import { useTranslations } from "next-intl";
import { useId, useState } from "react";

import { Button } from "../button/button";
import { Dialog } from "../dialog/dialog";
import { SelectField, type SelectOption } from "../field/field";
import styles from "./reject-dialog.module.css";

interface RejectDialogProps {
  open: boolean;
  candidate: string;
  /** The person who will be recorded as deciding. */
  actor: string;
  /** When, already formatted for the locale: "today 14:32". */
  when: string;
  reasons: readonly SelectOption[];
  /** Days before the candidate is told, when the notice is left on. */
  notifyAfterDays?: number;
  recording?: boolean;
  onCancel: () => void;
  onConfirm: (decision: { reason: string; notify: boolean }) => void;
}

/**
 * Rejection is a deliberate human act that records who did it (FR-023 in the Phase 1 spec). Focus
 * opens on "Keep candidate"; "Reject candidate" stays disabled until a reason is chosen, and is the
 * only filled red in the product.
 */
export function RejectDialog({
  open,
  candidate,
  actor,
  when,
  reasons,
  notifyAfterDays = 3,
  recording = false,
  onCancel,
  onConfirm,
}: RejectDialogProps) {
  const t = useTranslations("reject");
  const notifyId = useId();
  const [reason, setReason] = useState("");
  const [notify, setNotify] = useState(true);

  // The dialog stays mounted between uses. Each opening starts from nothing chosen, so a reason
  // picked for one candidate can never pre-arm the reject button for the next.
  const [wasOpen, setWasOpen] = useState(open);
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) {
      setReason("");
      setNotify(true);
    }
  }

  return (
    <Dialog
      open={open}
      title={t("title", { name: candidate })}
      onClose={onCancel}
      actions={
        <>
          <Button variant="secondary" onClick={onCancel} autoFocus>
            {t("keep")}
          </Button>
          <Button
            variant="destructiveConfirm"
            disabled={reason === ""}
            loading={recording}
            loadingLabel={t("recording")}
            onClick={() => {
              onConfirm({ reason, notify });
            }}
          >
            {t("confirm")}
          </Button>
        </>
      }
    >
      <p>{t("body")}</p>
      <SelectField
        label={t("reason")}
        placeholder={t("chooseReason")}
        options={reasons}
        value={reason}
        required
        onChange={(event) => {
          setReason(event.target.value);
        }}
      />
      <div className={styles.check}>
        <input
          id={notifyId}
          type="checkbox"
          checked={notify}
          onChange={(event) => {
            setNotify(event.target.checked);
          }}
        />
        <label htmlFor={notifyId}>{t("notify", { days: notifyAfterDays })}</label>
      </div>
      <p className={styles.recorded}>{t("recorded", { actor, when })}</p>
    </Dialog>
  );
}
