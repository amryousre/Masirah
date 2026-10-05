"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "../button/button";
import { Dialog } from "../dialog/dialog";
import styles from "./delete-candidate-data.module.css";

interface DeleteCandidateDataProps {
  /** The candidate's name as the reader knows them. */
  candidate: string;
  /** Records the request; true once it is recorded. */
  onDelete: () => Promise<boolean>;
  /** Why the last request was not recorded; shown inside the confirmation. */
  error?: string | undefined;
}

/**
 * A candidate's personal data deleted on their request (T101, T102, FR-076). Before anything is
 * asked it says what is deleted for good and what the audit trail keeps, as the settings design
 * lists them; the confirmation then states the consequence rather than asking "are you sure".
 */
export function DeleteCandidateData({ candidate, onDelete, error }: DeleteCandidateDataProps) {
  const t = useTranslations("deletion");
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);

  return (
    <div className={styles.deletion}>
      <div className={styles.lists}>
        <section>
          <h3 className={styles.heading}>{t("deletedHeading")}</h3>
          <ul className={styles.list}>
            <li>{t("deleted.identity")}</li>
            <li>{t("deleted.cv")}</li>
            <li>{t("deleted.scores")}</li>
          </ul>
        </section>
        <section>
          <h3 className={styles.heading}>{t("keptHeading")}</h3>
          <ul className={styles.list}>
            <li>{t("kept.record")}</li>
            <li>{t("kept.decisions")}</li>
          </ul>
        </section>
      </div>
      <div>
        <Button
          variant="destructive"
          onClick={() => {
            setOpen(true);
          }}
        >
          {t("open")}
        </Button>
      </div>
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
              error={error}
              onClick={() => {
                setPending(true);
                void onDelete().then((recorded) => {
                  setPending(false);
                  if (recorded) setOpen(false);
                });
              }}
            >
              {t("confirm")}
            </Button>
          </>
        }
      >
        <p>{t("consequence")}</p>
      </Dialog>
    </div>
  );
}
