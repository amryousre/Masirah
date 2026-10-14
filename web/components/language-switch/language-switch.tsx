"use client";

import { useLocale, useTranslations } from "next-intl";
import { useLinkStatus } from "next/link";

import { Link, usePathname } from "@/i18n/navigation";
import { type Locale, routing } from "@/i18n/routing";

import { Icon } from "../icon/icon";
import styles from "./language-switch.module.css";

/**
 * Names the other language in its own script ("English" on an Arabic page, "العربية" on an
 * English one) and opens the same page in it. Present on every screen.
 *
 * Its seven states (T107): hover, focus and active are styles; loading shows while the other
 * language opens. Disabled keeps the name in view but leads nowhere, for a screen that must not be
 * left mid-task. Failed says the page stayed in its language, and the switch can be tried again.
 */
export function LanguageSwitch({
  disabled = false,
  failed = false,
}: {
  disabled?: boolean;
  failed?: boolean;
}) {
  const t = useTranslations("language");
  const locale = useLocale();
  const pathname = usePathname();
  const other: Locale = routing.locales.find((candidate) => candidate !== locale) ?? locale;

  if (disabled) {
    return (
      <span className={styles.switch} aria-disabled="true">
        <Icon name="globe" size={16} strokeWidth={1.75} />
        <span lang={other}>{t("other")}</span>
      </span>
    );
  }

  return (
    <span className={styles.wrap}>
      <Link href={pathname} locale={other} hrefLang={other} className={styles.switch}>
        <SwitchLabel lang={other} label={t("other")} pendingLabel={t("switching")} />
      </Link>
      {failed && (
        <span role="alert" className={styles.failed}>
          <Icon name="alert" size={14} strokeWidth={2.25} />
          {t("failed")}
        </span>
      )}
    </span>
  );
}

function SwitchLabel({
  lang,
  label,
  pendingLabel,
}: {
  lang: Locale;
  label: string;
  pendingLabel: string;
}) {
  const { pending } = useLinkStatus();
  return (
    <>
      <Icon name={pending ? "spinner" : "globe"} size={16} strokeWidth={1.75} />
      <span lang={lang}>{label}</span>
      {pending && <span className={styles.pending}>{pendingLabel}</span>}
    </>
  );
}
