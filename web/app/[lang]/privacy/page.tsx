import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";

import { AuthFrame, AuthHeading } from "@/components/auth-frame/auth-frame";
import { routing } from "@/i18n/routing";

import styles from "./privacy.module.css";

export async function generateMetadata({
  params,
}: PageProps<"/[lang]/privacy">): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "privacyPolicy" });
  return { title: t("title") };
}

const SECTIONS = ["who", "what", "use", "ai", "where", "retention", "rights", "waitlist"] as const;

// The privacy page for candidates (T094, AI-09): what happens to a CV an employer screens with
// Masirah, including that the model providers do not train on it. Public, so a candidate can read
// it without an account. The provider statements follow pipeline/src/masirah_pipeline/adapters/
// README.md; change both together.
export default async function PrivacyPage({ params }: PageProps<"/[lang]/privacy">) {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "privacyPolicy" });

  return (
    <AuthFrame width="reading">
      <AuthHeading title={t("title")}>{t("lede")}</AuthHeading>
      {SECTIONS.map((section) => (
        <section key={section} className={styles.section} aria-labelledby={`privacy-${section}`}>
          <h2 id={`privacy-${section}`} className={styles.title}>
            {t(`${section}.title`)}
          </h2>
          <p className={styles.body}>{t(`${section}.body`)}</p>
          {section === "use" && <p className={styles.body}>{t("use.fairness")}</p>}
        </section>
      ))}
      <p className={styles.updated}>{t("updated")}</p>
    </AuthFrame>
  );
}
