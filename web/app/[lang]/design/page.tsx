import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";

import { Button, type ButtonVariant } from "@/components/button/button";
import { SelectField, TextField } from "@/components/field/field";
import { ScoreBreakdown } from "@/components/score/score";
import { LanguageSwitch } from "@/components/language-switch/language-switch";
import {
  Confidence,
  Decision,
  DocumentStatus,
  type DocumentStatusKind,
} from "@/components/status/status";
import { Link } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";

import { DialogDemo, TabsDemo, ToastsDemo } from "./demos";
import { CandidatesDemo, EvidenceDemo, RejectDemo, UploadDemo, UsageDemo } from "./screening-demos";
import styles from "./design.module.css";

export async function generateMetadata({ params }: PageProps<"/[lang]/design">): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "gallery" });
  return { title: t("title") };
}

const documentStatuses: DocumentStatusKind[] = [
  "queued",
  "processing",
  "parsed",
  "needsReview",
  "failed",
  "unsupportedLanguage",
];

const buttonRows: { variant: ButtonVariant; label: string; progress: string }[] = [
  { variant: "primary", label: "saveJob", progress: "saving" },
  { variant: "secondary", label: "uploadCvs", progress: "uploading" },
  { variant: "ghost", label: "cancel", progress: "cancelling" },
  { variant: "destructive", label: "rejectCandidate", progress: "recording" },
];

function Section({ title, note, children }: { title: string; note: string; children: ReactNode }) {
  return (
    <section className={styles.section}>
      <div className={styles.sectionHead}>
        <h2 className={styles.sectionTitle}>{title}</h2>
        <p className={styles.note}>{note}</p>
      </div>
      <div className={styles.specimens}>{children}</div>
    </section>
  );
}

export default async function DesignSystem({ params }: PageProps<"/[lang]/design">) {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations("gallery");
  const meta = await getTranslations("meta");
  const states = ["default", "disabled", "loading", "error"] as const;
  const languageOptions = [
    { value: "ar", label: t("fields.arabic") },
    { value: "en", label: t("fields.english") },
    { value: "both", label: t("fields.both") },
  ];

  return (
    <>
      <header className={styles.bar}>
        <span className={styles.product}>{meta("product")}</span>
        <LanguageSwitch />
      </header>

      <main className={styles.main}>
        <div className={styles.intro}>
          <h1 className={styles.title}>{t("title")}</h1>
          <p className={styles.lede}>{t("intro")}</p>
          <p className={styles.note}>{t("statesNote")}</p>
          <Link href="/design/frame" className={styles.frameLink}>
            {t("frameLink")}
          </Link>
        </div>

        <Section title={t("buttons.title")} note={t("buttons.note")}>
          <table className={styles.matrix}>
            <thead>
              <tr>
                <td />
                {states.map((state) => (
                  <th key={state} scope="col">
                    {t(`states.${state}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {buttonRows.map(({ variant, label, progress }) => {
                const text = t(`buttons.${label}` as "buttons.saveJob");
                const verb = t(`buttons.${progress}` as "buttons.saving");
                return (
                  <tr key={variant}>
                    <th scope="row">{t(`variants.${variant}` as "variants.primary")}</th>
                    <td>
                      <Button variant={variant} loadingLabel={verb}>
                        {text}
                      </Button>
                    </td>
                    <td>
                      <Button variant={variant} loadingLabel={verb} disabled>
                        {text}
                      </Button>
                    </td>
                    <td>
                      <Button variant={variant} loadingLabel={verb} loading>
                        {text}
                      </Button>
                    </td>
                    <td>
                      <Button variant={variant} loadingLabel={verb} error={t("buttons.saveFailed")}>
                        {text}
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Section>

        <Section title={t("fields.title")} note={t("fields.note")}>
          <div className={styles.grid}>
            <TextField
              label={t("fields.jobTitle")}
              help={t("fields.jobTitleHelp")}
              defaultValue={t("fields.jobTitleValue")}
            />
            <TextField
              label={t("fields.jobTitle")}
              help={t("fields.jobTitleLocked")}
              defaultValue={t("fields.jobTitleValue")}
              disabled
            />
            <TextField
              label={t("fields.jobTitle")}
              loading={t("fields.jobTitleChecking")}
              defaultValue={t("fields.jobTitleValue")}
            />
            <TextField
              label={t("fields.jobTitle")}
              error={t("fields.jobTitleMissing")}
              defaultValue=""
            />
            <SelectField
              label={t("fields.language")}
              help={t("fields.languageHelp")}
              options={languageOptions}
              defaultValue=""
            />
            <SelectField
              label={t("fields.language")}
              help={t("fields.languageLocked")}
              options={languageOptions}
              defaultValue="both"
              disabled
            />
            <SelectField
              label={t("fields.language")}
              loading={t("fields.languageLoading")}
              options={languageOptions}
              defaultValue=""
            />
            <SelectField
              label={t("fields.language")}
              error={t("fields.languageMissing")}
              options={languageOptions}
              defaultValue=""
            />
            <TextField
              label={t("fields.location")}
              help={t("fields.locationHelp")}
              defaultValue={t("fields.locationValue")}
              suggested
            />
          </div>
        </Section>

        <Section title={t("tabs.title")} note={t("tabs.note")}>
          <TabsDemo />
        </Section>

        <Section title={t("status.title")} note={t("status.note")}>
          <dl className={styles.statusGroups}>
            <div>
              <dt>{t("status.documents")}</dt>
              {documentStatuses.map((status) => (
                <dd key={status}>
                  <DocumentStatus status={status} />
                </dd>
              ))}
            </div>
            <div>
              <dt>{t("status.confidence")}</dt>
              <dd>
                <Confidence level="high" />
              </dd>
              <dd>
                <Confidence level="medium" />
              </dd>
              <dd>
                <Confidence level="low" showHint />
              </dd>
            </div>
            <div>
              <dt>{t("status.decisions")}</dt>
              <dd>
                <Decision kind="undecided" detailed />
              </dd>
              <dd>
                <Decision kind="shortlisted" by={t("status.tarek")} when={t("status.tarekWhen")} />
              </dd>
              <dd>
                <Decision kind="rejected" by={t("status.nourhan")} when={t("status.nourhanWhen")} />
              </dd>
            </div>
          </dl>
        </Section>

        <Section title={t("candidates.title")} note={t("candidates.note")}>
          <CandidatesDemo />
        </Section>

        <Section title={t("evidence.title")} note={t("evidence.note")}>
          <EvidenceDemo />
        </Section>

        <Section title={t("score.title")} note={t("score.note")}>
          <div className={styles.grid}>
            <ScoreBreakdown
              total={78}
              parts={[
                { key: "skills", earned: 26, weight: 30 },
                { key: "experience", earned: 19, weight: 25 },
                { key: "education", earned: 12, weight: 15 },
                { key: "tenure", earned: 8, weight: 10 },
                { key: "language", earned: 8, weight: 10 },
                { key: "location", earned: 5, weight: 10 },
              ]}
            />
            <div className={styles.stack}>
              <ScoreBreakdown state="calculating" />
              <ScoreBreakdown state="unavailable" reason={t("score.unavailableReason")} />
            </div>
          </div>
        </Section>

        <Section title={t("upload.title")} note={t("upload.note")}>
          <UploadDemo />
        </Section>

        <Section title={t("usage.title")} note={t("usage.note")}>
          <UsageDemo />
        </Section>

        <Section title={t("reject.title")} note={t("reject.note")}>
          <RejectDemo />
        </Section>

        <Section title={t("dialog.title")} note={t("dialog.note")}>
          <DialogDemo />
        </Section>

        <Section title={t("toasts.title")} note={t("toasts.note")}>
          <ToastsDemo />
        </Section>

        <Section title={t("switcher.title")} note={t("switcher.note")}>
          <LanguageSwitch />
        </Section>
      </main>
    </>
  );
}
