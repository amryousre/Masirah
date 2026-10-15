import type { ReactNode } from "react";

import { LanguageSwitch } from "../language-switch/language-switch";
import { Logo } from "../logo/logo";
import styles from "./auth-frame.module.css";

/**
 * The frame around the screens before the product: sign-in and its outcomes. The logo at the
 * reading start, the language switch at the end, and one narrow column of content. A page
 * of text to read, such as the privacy page, takes a reading-width column instead.
 */
export function AuthFrame({
  children,
  width = "narrow",
}: {
  children: ReactNode;
  width?: "narrow" | "reading";
}) {
  return (
    <div className={styles.frame}>
      <header className={styles.header}>
        <Logo />
        <LanguageSwitch />
      </header>
      <main className={styles.main}>
        <div className={width === "reading" ? styles.reading : styles.column}>{children}</div>
      </main>
    </div>
  );
}

/** The heading block that opens each of these screens. */
export function AuthHeading({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className={styles.heading}>
      <h1 className={styles.title}>{title}</h1>
      {children !== undefined && <p className={styles.lede}>{children}</p>}
    </div>
  );
}
