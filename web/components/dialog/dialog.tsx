"use client";

import { useTranslations } from "next-intl";
import { type ReactNode, type SyntheticEvent, useEffect, useId, useRef } from "react";

import { Icon } from "../icon/icon";
import styles from "./dialog.module.css";

interface DialogProps {
  open: boolean;
  title: string;
  /** Called for Escape and for the close button. The caller decides whether to close. */
  onClose: () => void;
  children: ReactNode;
  /** The footer buttons, safe choice first. Give the safe one `autoFocus`. */
  actions?: ReactNode;
}

/**
 * A native modal dialog: the browser traps focus, blocks the page behind it and returns focus to
 * whatever opened it. Modals are a last resort in this product; the reject confirmation is the
 * case they exist for.
 */
export function Dialog({ open, title, onClose, children, actions }: DialogProps) {
  const t = useTranslations("dialog");
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const onCancel = (event: SyntheticEvent<HTMLDialogElement>) => {
    // Escape: keep the dialog under React's control rather than letting the browser close it.
    event.preventDefault();
    onClose();
  };

  return (
    <dialog ref={ref} aria-labelledby={titleId} className={styles.dialog} onCancel={onCancel}>
      <header className={styles.header}>
        <h2 id={titleId} className={styles.title}>
          {title}
        </h2>
        <button type="button" className={styles.close} aria-label={t("close")} onClick={onClose}>
          <Icon name="close" size={16} />
        </button>
      </header>
      <div className={styles.body}>{children}</div>
      {actions && <footer className={styles.actions}>{actions}</footer>}
    </dialog>
  );
}
