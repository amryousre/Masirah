import type { Metadata } from "next";
import { notFound, unstable_rethrow } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";

import { LanguageSwitch } from "@/components/language-switch/language-switch";
import { Logo } from "@/components/logo/logo";
import { Link, redirect } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { getAccess } from "@/lib/adapters/session";
import { reportError } from "@/lib/adapters/telemetry";

import { joinTheWaitlist } from "./_landing/actions";
import styles from "./_landing/landing.module.css";
import { RankingDemo } from "./_landing/ranking-demo";
import { WaitlistForm } from "./_landing/waitlist-form";

export async function generateMetadata({ params }: PageProps<"/[lang]">): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "landing" });
  return { title: { absolute: t("title") } };
}

/**
 * Whether the visitor is a member, who goes to their jobs instead. A public page must still render
 * when the session can't be read, so a failed lookup shows the page rather than an error.
 */
async function isMember(): Promise<boolean> {
  try {
    return (await getAccess()).kind === "member";
  } catch (error) {
    // Next.js signals with errors too (this page reads cookies, so it renders per request); those
    // go on, and only a failed lookup is caught.
    unstable_rethrow(error);
    reportError("the landing page could not read the session; showing it to a visitor", {}, error);
    return false;
  }
}

const TODAY = ["forty", "late", "trust"] as const;
const STEPS = ["create", "add", "read", "decide"] as const;
const ADVICE = ["evidence", "excluded", "nothingLost", "unsure"] as const;

// masirah.online's first page, in the website register (DESIGN.md section 7): what Masirah does, a
// way in for invited recruiters, and a waitlist for companies that want an account. Members go
// straight to their jobs. It promises nothing the product doesn't do: no pricing, no plans.
export default async function LandingPage({ params }: PageProps<"/[lang]">) {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  if (await isMember()) redirect({ href: "/jobs", locale: lang });

  const t = await getTranslations({ locale: lang, namespace: "landing" });
  const join = joinTheWaitlist.bind(null, lang);

  return (
    <div className={styles.page}>
      <header className={styles.bar}>
        <Link href="/" className={styles.home} aria-label={t("title")}>
          <Logo />
        </Link>
        <nav className={styles.nav}>
          <a href="#how" className={styles.navLink}>
            {t("nav.how")}
          </a>
          <LanguageSwitch />
          <Link href="/sign-in" className={styles.signIn}>
            {t("nav.signIn")}
          </Link>
        </nav>
      </header>

      <main>
        <section className={styles.hero}>
          <div className={styles.pitch}>
            <h1 className={styles.headline}>{t("hero.title")}</h1>
            <p className={styles.lede}>{t("hero.lede")}</p>
            <WaitlistForm action={join} invite />
          </div>
          <RankingDemo />
        </section>

        <section className={styles.split} aria-labelledby="landing-today">
          <h2 id="landing-today" className={styles.sectionTitle}>
            {t("today.title")}
          </h2>
          <ul className={styles.today}>
            {TODAY.map((key) => (
              <li key={key} className={styles.point}>
                <h3 className={styles.pointTitle}>{t(`today.${key}.title`)}</h3>
                <p className={styles.pointBody}>{t(`today.${key}.body`)}</p>
              </li>
            ))}
          </ul>
        </section>

        <section id="how" className={styles.band} aria-labelledby="landing-how">
          <div className={styles.bandInner}>
            <h2 id="landing-how" className={styles.sectionTitle}>
              {t("how.title")}
            </h2>
            {/* A real sequence, so the steps carry their numbers. */}
            <ol className={styles.steps}>
              {STEPS.map((key) => (
                <li key={key} className={styles.step}>
                  <h3 className={styles.pointTitle}>{t(`how.${key}.title`)}</h3>
                  <p className={styles.pointBody}>{t(`how.${key}.body`)}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className={styles.split} aria-labelledby="landing-advice">
          <h2 id="landing-advice" className={styles.sectionTitle}>
            {t("advice.title")}
          </h2>
          <ul className={styles.advice}>
            {ADVICE.map((key) => (
              <li key={key} className={styles.point}>
                <h3 className={styles.pointTitle}>{t(`advice.${key}.title`)}</h3>
                <p className={styles.pointBody}>{t(`advice.${key}.body`)}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className={styles.closing} aria-labelledby="landing-closing">
          <h2 id="landing-closing" className={styles.sectionTitle}>
            {t("closing.title")}
          </h2>
          <WaitlistForm action={join} labelledBy="landing-closing" />
        </section>
      </main>

      <footer className={styles.footer}>
        <span>{t("footer.copyright")}</span>
        <Link href="/privacy" className={styles.footerLink}>
          {t("footer.privacy")}
        </Link>
      </footer>
    </div>
  );
}
