"use client";

import { useTranslations } from "next-intl";
import { useActionState, useState } from "react";

import { Button, SubmitButton } from "@/components/button/button";
import { ButtonLink } from "@/components/button/button-link";
import { TextAreaField, TextField } from "@/components/field/field";
import { isolated } from "@/components/corrected-field/corrected-field";
import { Icon } from "@/components/icon/icon";
import { ENTRY_PARTS, type EntryKey } from "@/lib/domain/corrections";

import type { CorrectionState } from "./actions";
import styles from "./edit.module.css";

export type FormEntry = Record<string, string>;

export interface FormValues {
  name: string;
  location: string;
  years_of_experience: string;
  emails: string;
  phones: string;
  skills: string;
  employment: FormEntry[];
  education: FormEntry[];
  languages: FormEntry[];
  certifications: FormEntry[];
}

/** A corrected field's note: what extraction read, who corrected it and when. */
export interface FieldNote {
  extracted: string[];
  by: string;
  when: string;
}

const GROUPS: EntryKey[] = ["employment", "education", "languages", "certifications"];

interface CorrectionFormProps {
  action: (state: CorrectionState, form: FormData) => Promise<CorrectionState>;
  values: FormValues;
  notes: Partial<Record<string, FieldNote>>;
  back: string;
}

/** The candidate's details as corrected so far, every field editable (T082, FR-010). */
export function CorrectionForm({ action, values, notes, back }: CorrectionFormProps) {
  const t = useTranslations("correct");
  const tCorrected = useTranslations("corrected");
  const [state, submit] = useActionState(action, { status: "idle" });
  const errors = state.status === "invalid" ? state.errors : {};

  // A corrected field says so, and what was read, where its help would be. Each value is set
  // apart in its own direction, so an email or a date keeps its order inside Arabic text.
  const note = (field: string, help?: string) => {
    const corrected = notes[field];
    if (corrected === undefined) return help;
    const read =
      corrected.extracted.length === 0
        ? tCorrected("extractedNothing")
        : tCorrected("extracted", { value: isolated(corrected.extracted.join("; ")) });
    const who = tCorrected("byWhom", {
      name: isolated(corrected.by),
      when: isolated(corrected.when),
    });
    return `${tCorrected("corrected")} · ${who}. ${read}${help === undefined ? "" : ` ${help}`}`;
  };
  const error = (field: keyof typeof errors) => {
    const code = errors[field];
    return code === undefined ? undefined : t(`errors.${code}`);
  };

  return (
    <form action={submit} className={styles.form} noValidate>
      {state.status !== "idle" && (
        <p className={styles.alert} role="alert">
          <Icon name="alert" size={16} />
          {state.status === "failed" ? t("errors.save") : t("errors.summary")}
        </p>
      )}

      <section className={styles.section}>
        <TextField
          name="name"
          label={t("fields.name")}
          defaultValue={values.name}
          help={note("name")}
          autoComplete="off"
          wide
        />
        <TextField
          name="location"
          label={t("fields.location")}
          defaultValue={values.location}
          help={note("location")}
          autoComplete="off"
          wide
        />
        <TextField
          name="years_of_experience"
          label={t("fields.years_of_experience")}
          defaultValue={values.years_of_experience}
          inputMode="numeric"
          wide
          help={note("years_of_experience", t("yearsHelp"))}
          error={error("years_of_experience")}
        />
        <TextAreaField
          name="emails"
          wide
          label={t("fields.emails")}
          defaultValue={values.emails}
          rows={2}
          dir="ltr"
          help={note("emails", t("onePerLine"))}
          error={error("emails")}
        />
        <TextAreaField
          name="phones"
          wide
          label={t("fields.phones")}
          defaultValue={values.phones}
          rows={2}
          dir="ltr"
          help={note("phones", t("onePerLine"))}
        />
        <TextAreaField
          name="skills"
          wide
          label={t("fields.skills")}
          defaultValue={values.skills}
          rows={4}
          help={note("skills", t("onePerLine"))}
        />
      </section>

      {GROUPS.map((group) => (
        <EntryGroup
          key={group}
          group={group}
          initial={values[group]}
          note={note(
            group,
            group === "employment" || group === "education" ? t("dateHelp") : undefined,
          )}
          error={error(group)}
        />
      ))}

      <div className={styles.actions}>
        <SubmitButton variant="primary" loadingLabel={t("saving")}>
          {t("save")}
        </SubmitButton>
        <ButtonLink href={back}>{t("cancel")}</ButtonLink>
      </div>
    </form>
  );
}

function EntryGroup({
  group,
  initial,
  note,
  error,
}: {
  group: EntryKey;
  initial: FormEntry[];
  note: string | undefined;
  error: string | undefined;
}) {
  const t = useTranslations("correct");
  // Each row keeps the index it was given, so removing one never renames another's fields.
  const [rows, setRows] = useState(() => initial.map((entry, index) => ({ index, entry })));
  const [next, setNext] = useState(initial.length);
  const legendId = `${group}-legend`;
  const messageId = `${group}-message`;
  const message = error ?? note;

  return (
    <div className={styles.groupFrame}>
      <fieldset
        className={styles.group}
        aria-labelledby={legendId}
        aria-describedby={message === undefined ? undefined : messageId}
        aria-invalid={error === undefined ? undefined : true}
      >
        <legend id={legendId} className={styles.legend}>
          {t(`fields.${group}`)}
        </legend>
        {message !== undefined && (
          <p id={messageId} className={error === undefined ? styles.help : styles.error}>
            {error !== undefined && <Icon name="alert" size={12} strokeWidth={2.25} />}
            {message}
          </p>
        )}
        {rows.map(({ index, entry }, position) => (
          <div key={index} className={styles.entry} data-parts={ENTRY_PARTS[group].length}>
            <p className={styles.entryTitle}>{t("entry", { number: position + 1 })}</p>
            <div className={styles.parts}>
              {ENTRY_PARTS[group].map((part) => (
                <TextField
                  key={part}
                  name={`${group}.${String(index)}.${part}`}
                  label={t(`parts.${part}`)}
                  defaultValue={entry[part] ?? ""}
                  autoComplete="off"
                />
              ))}
            </div>
            <Button
              variant="ghost"
              className={styles.remove}
              onClick={() => {
                setRows((current) => current.filter((row) => row.index !== index));
              }}
            >
              {t("removeEntry", { number: position + 1 })}
            </Button>
          </div>
        ))}
        <Button
          className={styles.add}
          onClick={() => {
            setRows((current) => [...current, { index: next, entry: {} }]);
            setNext(next + 1);
          }}
        >
          {t(`add.${group}`)}
        </Button>
      </fieldset>
    </div>
  );
}
