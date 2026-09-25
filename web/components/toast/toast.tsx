"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { cx } from "../cx";
import { Icon, type IconName } from "../icon/icon";
import styles from "./toast.module.css";

export type ToastTone = "success" | "neutral" | "error";

const toneIcon: Record<ToastTone, IconName> = {
  success: "checkCircle",
  neutral: "minusCircle",
  error: "xCircle",
};

interface ToastProps {
  tone: ToastTone;
  /** A fact, not a celebration: "24 of 25 files are processed. One needs review." */
  message: string;
  /** At most one action, such as "Undo" or "Try again". */
  action?: { label: string; onAction: () => void };
  onDismiss?: () => void;
}

/** Failures are announced at once; everything else waits for a pause in speech. */
export function Toast({ tone, message, action, onDismiss }: ToastProps) {
  const t = useTranslations("toast");
  return (
    <div role={tone === "error" ? "alert" : "status"} className={styles.toast} data-tone={tone}>
      <Icon name={toneIcon[tone]} size={16} className={styles.icon} />
      <p className={styles.message}>{message}</p>
      {action && (
        <button type="button" className={styles.action} onClick={action.onAction}>
          {action.label}
        </button>
      )}
      {onDismiss && (
        <button
          type="button"
          className={styles.dismiss}
          aria-label={t("dismiss")}
          onClick={onDismiss}
        >
          <Icon name="close" size={14} />
        </button>
      )}
    </div>
  );
}

interface ToastRegionProps {
  children: ReactNode;
  /** Fixed to the page corner by default; `inline` keeps it in the flow, as on the design page. */
  placement?: "fixed" | "inline";
}

export function ToastRegion({ children, placement = "fixed" }: ToastRegionProps) {
  const t = useTranslations("toast");
  return (
    <section aria-label={t("region")} className={cx(styles.region, styles[placement])}>
      {children}
    </section>
  );
}
