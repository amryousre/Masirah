"use client";

import { useTranslations } from "next-intl";
import { useActionState, useId } from "react";

import { SubmitButton } from "@/components/button/button";
import { Icon } from "@/components/icon/icon";

import type { WaitlistState } from "./actions";
import styles from "./landing.module.css";

interface WaitlistFormProps {
  action: (previous: WaitlistState, form: FormData) => Promise<WaitlistState>;
  /** Shown above the form, as the hero's invitation; the closing call to action has its own. */
  invite?: boolean;
  /** The element naming this form, when not the form's own name: two forms must not share one. */
  labelledBy?: string;
}

/**
 * A work email, and nothing else (migration 0027). The server checks it and answers in the page's
 * language; the browser's own messages would arrive in the browser's language instead.
 */
export function WaitlistForm({ action, invite = false, labelledBy }: WaitlistFormProps) {
  const t = useTranslations("landing.waitlist");
  const [state, formAction] = useActionState(action, { email: "" });
  const inputId = useId();
  const messageId = useId();
  const refused = state.outcome === "invalid" || state.outcome === "unavailable";

  return (
    <form
      action={formAction}
      noValidate
      {...(labelledBy === undefined
        ? { "aria-label": t("name") }
        : { "aria-labelledby": labelledBy })}
      className={styles.waitlist}
    >
      {invite && <p className={styles.invite}>{t("invite")}</p>}
      {state.outcome === "joined" ? (
        <p role="status" className={styles.joined}>
          <Icon name="checkCircle" size={16} strokeWidth={2} />
          {t("joined")}
        </p>
      ) : (
        <>
          <div className={styles.row}>
            <label htmlFor={inputId} className={styles.hidden}>
              {t("email")}
            </label>
            <input
              id={inputId}
              name="email"
              type="email"
              autoComplete="email"
              inputMode="email"
              spellCheck={false}
              // An address reads left to right in both languages (DESIGN.md section 4).
              dir="ltr"
              placeholder={t("placeholder")}
              defaultValue={state.email}
              aria-invalid={refused || undefined}
              aria-describedby={refused ? messageId : undefined}
              required
              className={styles.input}
            />
            <SubmitButton variant="primary" loadingLabel={t("submitting")}>
              {t("submit")}
            </SubmitButton>
          </div>
          {refused ? (
            <p id={messageId} role="alert" className={styles.refused}>
              <Icon name="alert" size={14} strokeWidth={2.25} />
              {t(state.outcome)}
            </p>
          ) : (
            <p className={styles.fine}>{t("fine")}</p>
          )}
        </>
      )}
    </form>
  );
}
