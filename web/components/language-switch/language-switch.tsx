"use client";

import { useLocale, useTranslations } from "next-intl";
import { useLinkStatus } from "next/link";
import { type MouseEvent, useId, useState } from "react";

import { Link, usePathname } from "@/i18n/navigation";
import { type Locale, routing } from "@/i18n/routing";

import { Icon } from "../icon/icon";
import styles from "./language-switch.module.css";

/**
 * Names the other language in its own script ("English" on an Arabic page, "العربية" on an
 * English one) and opens the same page in it. Present on every screen.
 *
 * Its seven states (T107): hover, focus and active are styles, and loading shows while the other
 * language opens. Disabled keeps the name in view but leads nowhere, for a screen that must not be
 * left mid-task. It fails when there is no connection to open the other language with: the page
 * stays as it is and says so, and the switch can be tried again. `failed` shows that message
 * without announcing it, for the design page's specimen.
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
  const messageId = useId();
  const [offline, setOffline] = useState(false);
  const other: Locale = routing.locales.find((candidate) => candidate !== locale) ?? locale;

  if (disabled) {
    return (
      // A link that leads nowhere: still reached by Tab and announced as unavailable.
      <a role="link" aria-disabled="true" tabIndex={0} className={styles.switch}>
        <Icon name="globe" size={16} strokeWidth={1.75} />
        <span lang={other}>{t("other")}</span>
      </a>
    );
  }

  // Opening the other language needs the server. Without a connection the page would be lost to
  // the browser's error screen, so it stays put and says why.
  const go = (event: MouseEvent<HTMLAnchorElement>) => {
    if (navigator.onLine) {
      setOffline(false);
      return;
    }
    event.preventDefault();
    setOffline(true);
  };

  const link = (
    <Link
      href={pathname}
      locale={other}
      hrefLang={other}
      className={styles.switch}
      onClick={go}
      aria-describedby={offline || failed ? messageId : undefined}
    >
      <SwitchLabel lang={other} label={t("other")} pendingLabel={t("switching")} />
    </Link>
  );
  // The message sits beside the link rather than wrapping it, so the link keeps its place in the
  // layout and stays the same element when the message appears.
  return (
    <>
      {link}
      {(offline || failed) && (
        <span id={messageId} role={offline ? "alert" : undefined} className={styles.failed}>
          <Icon name="alert" size={12} strokeWidth={2.25} />
          {t("failed")}
        </span>
      )}
    </>
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
