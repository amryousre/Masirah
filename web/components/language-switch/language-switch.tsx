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
 */
export function LanguageSwitch() {
  const t = useTranslations("language");
  const locale = useLocale();
  const pathname = usePathname();
  const other: Locale = routing.locales.find((candidate) => candidate !== locale) ?? locale;
  return (
    <Link href={pathname} locale={other} hrefLang={other} className={styles.switch}>
      <SwitchLabel lang={other} label={t("other")} pendingLabel={t("switching")} />
    </Link>
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
