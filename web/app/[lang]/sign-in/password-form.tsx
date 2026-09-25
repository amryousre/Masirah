"use client";

import { useTranslations } from "next-intl";
import { useActionState } from "react";

import { SubmitButton } from "@/components/button/button";
import { PasswordField, TextField } from "@/components/field/field";
import { Icon } from "@/components/icon/icon";

import type { PasswordSignInState } from "./actions";
import styles from "./sign-in.module.css";

interface PasswordFormProps {
  action: (previous: PasswordSignInState, form: FormData) => Promise<PasswordSignInState>;
}

export function PasswordForm({ action }: PasswordFormProps) {
  const t = useTranslations("signIn");
  const [state, formAction] = useActionState(action, { email: "" });

  return (
    // The server checks the fields and answers in the page's language; the browser's own
    // messages would arrive in the browser's language instead.
    <form action={formAction} noValidate className={styles.form}>
      <TextField
        label={t("email")}
        name="email"
        type="email"
        autoComplete="username"
        inputMode="email"
        spellCheck={false}
        // An address reads left to right in both languages (DESIGN.md section 4).
        dir="ltr"
        placeholder={t("emailPlaceholder")}
        defaultValue={state.email}
        required
      />
      <PasswordField
        label={t("password")}
        name="password"
        autoComplete="current-password"
        required
      />
      {state.error !== undefined && (
        <p role="alert" className={styles.alert}>
          <Icon name="alert" size={14} strokeWidth={2.25} className={styles.alertIcon} />
          {t(`errors.${state.error}`)}
        </p>
      )}
      <SubmitButton variant="primary" loadingLabel={t("submitProgress")} className={styles.wide}>
        {t("submit")}
      </SubmitButton>
    </form>
  );
}
