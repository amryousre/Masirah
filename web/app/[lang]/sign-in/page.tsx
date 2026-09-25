import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";

import { AuthFrame, AuthHeading } from "@/components/auth-frame/auth-frame";
import { SubmitButton } from "@/components/button/button";
import { GoogleMark } from "@/components/google-mark/google-mark";
import { Icon } from "@/components/icon/icon";
import { redirect } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { getAccess } from "@/lib/adapters/session";

import { signInWithGoogle, signInWithPassword } from "./actions";
import { PasswordForm } from "./password-form";
import styles from "./sign-in.module.css";

export async function generateMetadata({
  params,
}: PageProps<"/[lang]/sign-in">): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "signIn" });
  return { title: t("title") };
}

// Sign-in (T024): Google, or a work email and password. Access is by invitation, so there is no
// way to create an account here.
export default async function SignInPage({ params, searchParams }: PageProps<"/[lang]/sign-in">) {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  if ((await getAccess()).kind === "member") redirect({ href: "/jobs", locale: lang });

  const { error } = await searchParams;
  const t = await getTranslations({ locale: lang, namespace: "signIn" });

  return (
    <AuthFrame>
      <AuthHeading title={t("title")}>{t("lede")}</AuthHeading>
      {error === "google" && (
        <p role="alert" className={styles.alert}>
          <Icon name="alert" size={14} strokeWidth={2.25} className={styles.alertIcon} />
          {t("errors.google")}
        </p>
      )}
      <form action={signInWithGoogle.bind(null, lang)}>
        <SubmitButton loadingLabel={t("googleProgress")} className={styles.wide}>
          <GoogleMark />
          {t("google")}
        </SubmitButton>
      </form>
      <p className={styles.divider}>{t("or")}</p>
      <PasswordForm action={signInWithPassword.bind(null, lang)} />
      <p className={styles.note}>{t("inviteOnly")}</p>
    </AuthFrame>
  );
}
