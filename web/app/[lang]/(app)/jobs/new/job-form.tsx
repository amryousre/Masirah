"use client";

import { useLocale, useTranslations } from "next-intl";
import { useActionState, useState, useTransition } from "react";

import { Button } from "@/components/button/button";
import { SelectField, TextAreaField, TextField } from "@/components/field/field";
import { SkillsField } from "@/components/skills/skills-field";
import { Tabs } from "@/components/tabs/tabs";
import { type DraftProblem, LANGUAGE_REQUIREMENTS, LIMITS } from "@/lib/domain/job-draft";

import { createJob, type CreateJobState, proposeSpecification } from "./actions";
import styles from "./new-job.module.css";

const EXPERIENCE_YEARS = [1, 2, 3, 4, 5, 7, 10] as const;

type Mode = "paste" | "manual";

/**
 * Paste first, structure second (design-brief.md section 5). The paste tab takes a whole job
 * description and proposes the fields from it; the manual tab is the same form filled by hand.
 * When no proposal can be made, the pasted text is kept as the description and the form opens,
 * so nothing typed is lost.
 */
export function JobForm({ start }: { start: Mode }) {
  const t = useTranslations("newJob");
  const locale = useLocale();
  const [mode, setMode] = useState<Mode>(start);
  const [pasted, setPasted] = useState("");
  const [notice, setNotice] = useState(false);
  const [proposing, startProposing] = useTransition();
  const [state, save, saving] = useActionState<CreateJobState, FormData>(
    createJob.bind(null, locale),
    {},
  );

  const problem = (field: keyof NonNullable<CreateJobState["errors"]>, max?: number) => {
    const found: DraftProblem | undefined = state.errors?.[field];
    if (found === undefined) return undefined;
    return t(`error.${found}`, { max: max ?? 0 });
  };

  const propose = () => {
    startProposing(async () => {
      // Until T060 proposes fields, every proposal is unavailable: keep the text, open the form.
      await proposeSpecification(locale);
      setNotice(true);
      setMode("manual");
    });
  };

  const form = (
    <form action={save} className={styles.form} noValidate>
      {notice && (
        <p role="status" className={styles.notice}>
          {t("unavailable")}
        </p>
      )}
      <TextField
        label={t("field.title")}
        name="title"
        wide
        required
        maxLength={LIMITS.title}
        autoComplete="off"
        error={problem("title", LIMITS.title)}
      />
      <TextAreaField
        label={t("field.description")}
        name="description"
        rows={6}
        wide
        defaultValue={pasted}
        maxLength={LIMITS.description}
        error={problem("description", LIMITS.description)}
      />
      <div className={styles.pair}>
        <SkillsField
          label={t("field.requiredSkills")}
          name="requiredSkills"
          help={t("help.requiredSkills")}
          error={problem("requiredSkills", LIMITS.skills)}
        />
        <SkillsField
          label={t("field.preferredSkills")}
          name="preferredSkills"
          help={t("help.preferredSkills")}
          error={problem("preferredSkills", LIMITS.skills)}
        />
      </div>
      <div className={styles.pair}>
        <SelectField
          label={t("field.minimumExperience")}
          name="minimumExperienceYears"
          defaultValue=""
          options={EXPERIENCE_YEARS.map((years) => ({
            value: String(years),
            label: t("years", { years }),
          }))}
          error={problem("minimumExperienceYears")}
        />
        <TextField
          label={t("field.location")}
          name="location"
          maxLength={LIMITS.location}
          error={problem("location", LIMITS.location)}
        />
      </div>
      <SelectField
        label={t("field.languageRequirement")}
        name="languageRequirement"
        defaultValue=""
        options={LANGUAGE_REQUIREMENTS.map((code) => ({
          value: code,
          label: t(`language.${code}`),
        }))}
        error={problem("languageRequirement")}
      />
      <div className={styles.actions}>
        <Button
          type="submit"
          variant="primary"
          loading={saving}
          loadingLabel={t("saving")}
          error={state.failed ? t("failed") : undefined}
        >
          {t("save")}
        </Button>
      </div>
    </form>
  );

  return (
    <Tabs
      label={t("modes")}
      items={[
        { id: "paste", label: t("mode.paste") },
        { id: "manual", label: t("mode.manual") },
      ]}
      selected={mode}
      onSelect={(id) => {
        setMode(id === "manual" ? "manual" : "paste");
      }}
    >
      {mode === "manual" ? (
        form
      ) : (
        <div className={styles.form}>
          <TextAreaField
            label={t("field.pasted")}
            help={t("help.pasted")}
            rows={10}
            wide
            value={pasted}
            maxLength={LIMITS.description}
            onChange={(event) => {
              setPasted(event.target.value);
            }}
          />
          <div className={styles.actions}>
            <Button
              variant="primary"
              loading={proposing}
              loadingLabel={t("proposing")}
              disabled={pasted.trim() === ""}
              onClick={propose}
            >
              {t("propose")}
            </Button>
          </div>
        </div>
      )}
    </Tabs>
  );
}
