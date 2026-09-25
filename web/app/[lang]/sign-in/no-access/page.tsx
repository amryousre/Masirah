import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";

import { AuthFrame, AuthHeading } from "@/components/auth-frame/auth-frame";
import { SubmitButton } from "@/components/button/button";
import { routing } from "@/i18n/routing";

import { signOut } from "../actions";
import styles from "./no-access.module.css";

export async function generateMetadata({
  params,
}: PageProps<"/[lang]/sign-in/no-access">): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "noAccess" });
  return { title: t("title") };
}

// Where a sign-in without an invitation ends (T024). For a Google account nobody invited, Supabase
// Auth refused before creating a user, so the page can say truthfully that nothing was stored.
// It cannot name the address: Google told Supabase, not this app.
export default async function NoAccessPage({
  params,
  searchParams,
}: PageProps<"/[lang]/sign-in/no-access">) {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const { reason } = await searchParams;
  const t = await getTranslations({ locale: lang, namespace: "noAccess" });

  return (
    <AuthFrame>
      <AuthHeading title={t("title")}>
        {reason === "no-organisation" ? t("noOrganisation") : t("notInvited")}
      </AuthHeading>
      <section aria-labelledby="no-access-next" className={styles.next}>
        <h2 id="no-access-next" className={styles.nextTitle}>
          {t("next")}
        </h2>
        {/* role="list" keeps the list announced as one in Safari, which drops it without markers. */}
        <ol role="list" className={styles.steps}>
          <li>{t("askOwner")}</li>
          <li>{t("useInvited")}</li>
        </ol>
      </section>
      {/* Signing out first matters when a session exists, as it does for an account with no
          organisation; otherwise it is harmless. */}
      <form action={signOut.bind(null, lang)}>
        <SubmitButton loadingLabel={t("useAnotherProgress")}>{t("useAnother")}</SubmitButton>
      </form>
    </AuthFrame>
  );
}
