"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { Link, usePathname } from "@/i18n/navigation";

import { SubmitButton } from "../button/button";
import { Icon, type IconName } from "../icon/icon";
import { LanguageSwitch } from "../language-switch/language-switch";
import styles from "./app-frame.module.css";

interface AppFrameProps {
  organisation: string;
  /** The name comes from the identity provider; an email-and-password account has none. */
  user: { name: string | null; email: string };
  /** Documents waiting in the review queue, shown beside its link. */
  reviewCount?: number | undefined;
  /** Shown above the user: the usage meter, in practice. */
  usage?: ReactNode;
  /** Ends the session. A server action, so signing out works before any script has loaded. */
  signOut?: () => Promise<void>;
  children: ReactNode;
}

const sections: { href: string; label: "jobs" | "reviewQueue" | "settings"; icon: IconName }[] = [
  { href: "/jobs", label: "jobs", icon: "layers" },
  { href: "/review", label: "reviewQueue", icon: "alert" },
  { href: "/settings", label: "settings", icon: "gauge" },
];

function initials(name: string | null, email: string): string {
  if (name === null) return email.charAt(0).toLocaleUpperCase();
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word.charAt(0))
    .join("");
}

/**
 * The frame around every product screen: a sidebar at the reading start (the right in Arabic)
 * with the product, the organisation, the sections, usage, the user and the language switch.
 * On a phone the sidebar becomes a bar across the top and the sections a scrolling row.
 */
export function AppFrame({
  organisation,
  user,
  reviewCount,
  usage,
  signOut,
  children,
}: AppFrameProps) {
  const t = useTranslations("frame");
  const product = useTranslations("meta")("product");
  const pathname = usePathname();

  return (
    <div className={styles.frame}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.product}>{product}</span>
          <span className={styles.organisation}>{organisation}</span>
        </div>
        <nav aria-label={t("navigation")} className={styles.nav}>
          <ul>
            {sections.map((section) => {
              const current = pathname === section.href || pathname.startsWith(`${section.href}/`);
              return (
                <li key={section.href}>
                  <Link
                    href={section.href}
                    className={styles.link}
                    aria-current={current ? "page" : undefined}
                  >
                    <Icon name={section.icon} size={16} strokeWidth={1.75} />
                    <span className={styles.linkLabel}>{t(section.label)}</span>
                    {section.label === "reviewQueue" && reviewCount !== undefined && (
                      <span className={styles.count}>{reviewCount}</span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className={styles.footer}>
          {usage && <div className={styles.usage}>{usage}</div>}
          <div className={styles.user}>
            <span className={styles.avatar} aria-hidden="true">
              {initials(user.name, user.email)}
            </span>
            <span className={styles.identity}>
              <span className={styles.userName}>{user.name ?? user.email}</span>
              {user.name !== null && <span className={styles.email}>{user.email}</span>}
            </span>
          </div>
          {signOut && (
            <form action={signOut}>
              <SubmitButton
                variant="ghost"
                loadingLabel={t("signingOut")}
                className={styles.signOut}
              >
                {t("signOut")}
              </SubmitButton>
            </form>
          )}
          <LanguageSwitch />
        </div>
      </aside>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
