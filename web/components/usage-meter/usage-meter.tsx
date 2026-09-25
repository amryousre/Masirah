"use client";

import { useTranslations } from "next-intl";

import { Button } from "../button/button";
import { Icon } from "../icon/icon";
import styles from "./usage-meter.module.css";

type UsageMeterProps =
  | { loading: true }
  | {
      loading?: false;
      used: number;
      limit: number;
      /** When the monthly limit resets, already formatted for the locale: "1 Oct". */
      renewsOn: string;
      /** Files waiting because the limit is reached. */
      waiting?: number;
      onUpgrade?: () => void;
      onViewUsage?: () => void;
    };

const WARN_AT = 0.8;

/**
 * CVs processed against the monthly quota. From 80 percent the words change; at 100 percent it
 * says processing is paused and that nothing was lost. The bar stays grey, then ink: never red.
 */
export function UsageMeter(props: UsageMeterProps) {
  const t = useTranslations("usage");

  if (props.loading) {
    return (
      <div className={styles.meter} aria-busy="true">
        <p className={styles.label}>{t("label")}</p>
        <p className={styles.note}>
          <Icon name="spinner" size={12} strokeWidth={2.5} />
          {t("loading")}
        </p>
      </div>
    );
  }

  const { used, limit, renewsOn, waiting = 0, onUpgrade, onViewUsage } = props;
  const share = limit > 0 ? used / limit : 1;
  const state = share >= 1 ? "limit" : share >= WARN_AT ? "warning" : "normal";

  return (
    <div className={styles.meter} data-state={state}>
      <div className={styles.head}>
        <span className={styles.label}>{t("label")}</span>
        <span className={styles.count}>{t("count", { used, limit })}</span>
      </div>
      <div
        role="meter"
        aria-label={t("label")}
        aria-valuemin={0}
        aria-valuemax={limit}
        aria-valuenow={used}
        aria-valuetext={t("count", { used, limit })}
        className={styles.track}
        style={{ "--fill": `${String(Math.min(share, 1) * 100)}%` }}
      >
        <span className={styles.fill} />
        <span className={styles.tick} />
      </div>
      {state === "normal" && <p className={styles.note}>{t("renews", { date: renewsOn })}</p>}
      {state === "warning" && (
        <p className={styles.note}>
          <Icon name="alert" size={13} strokeWidth={2.25} />
          {t("remaining", { left: limit - used })}
        </p>
      )}
      {state === "limit" && (
        <>
          <p className={styles.note}>
            <Icon name="pauseCircle" size={13} strokeWidth={2.25} />
            {t("paused", { waiting, date: renewsOn })}
          </p>
          {(onUpgrade ?? onViewUsage) && (
            <div className={styles.actions}>
              {onUpgrade && (
                <Button variant="primary" onClick={onUpgrade}>
                  {t("upgrade")}
                </Button>
              )}
              {onViewUsage && (
                <Button variant="ghost" onClick={onViewUsage}>
                  {t("viewUsage")}
                </Button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
