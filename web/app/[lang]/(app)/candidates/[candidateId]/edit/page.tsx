import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getFormatter, getTranslations } from "next-intl/server";

import { routing } from "@/i18n/routing";
import { memberNames, readCorrectionTarget } from "@/lib/adapters/corrections";
import { getAccess } from "@/lib/adapters/session";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";
import {
  correctedProfile,
  correctedRows,
  ENTRY_PARTS,
  type EntryKey,
} from "@/lib/domain/corrections";

import { correctProfile } from "./actions";
import { CorrectionForm, type FormEntry, type FormValues, type FieldNote } from "./correction-form";
import styles from "./edit.module.css";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function generateMetadata({
  params,
}: PageProps<"/[lang]/candidates/[candidateId]/edit">): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "correct" });
  return { title: t("titleUnnamed") };
}

const text = (value: unknown) => (typeof value === "string" ? value : "");
const list = (value: unknown) =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];

// Correcting a candidate's extracted details (T082, FR-010). ?file= names the CV whose profile is
// corrected, and ?job= the job the member came from; without one the member returns to the
// review queue. Corrections are kept beside the extraction through correct_profile.
export default async function CorrectionPage({
  params,
  searchParams,
}: PageProps<"/[lang]/candidates/[candidateId]/edit">) {
  const { lang, candidateId } = await params;
  if (!hasLocale(routing.locales, lang) || !UUID.test(candidateId)) notFound();
  if ((await getAccess()).kind !== "member") return null;
  const { file, job } = await searchParams;
  const fileId = typeof file === "string" && UUID.test(file) ? file : null;
  const jobId = typeof job === "string" && UUID.test(job) ? job : null;

  const supabase = await createSupabaseServerClient();
  const target = await readCorrectionTarget(supabase, candidateId, fileId);
  if (target === null) notFound();
  const t = await getTranslations({ locale: lang, namespace: "correct" });
  const format = await getFormatter({ locale: lang });

  const back =
    jobId === null ? `/review?file=${target.file.id}` : `/jobs/${jobId}/candidates/${candidateId}`;
  const shown = correctedProfile(target.profile, target.corrections);
  const entries = (key: EntryKey): FormEntry[] =>
    (Array.isArray(shown[key]) ? (shown[key] as unknown[]) : []).map((entry) =>
      Object.fromEntries(
        ENTRY_PARTS[key].map((part) => {
          const value = text((entry as Record<string, unknown> | null)?.[part]);
          return [part, value === "present" ? t("present") : value];
        }),
      ),
    );
  const values: FormValues = {
    name: text(shown["name"]),
    location: text(shown["location"]),
    years_of_experience:
      typeof shown["years_of_experience"] === "number" ? String(shown["years_of_experience"]) : "",
    emails: list(shown["emails"]).join("\n"),
    phones: list(shown["phones"]).join("\n"),
    skills: list(shown["skills"]).join("\n"),
    employment: entries("employment"),
    education: entries("education"),
    languages: entries("languages"),
    certifications: entries("certifications"),
  };

  const names = await memberNames(
    supabase,
    Object.values(target.corrections).map((correction) => correction.by),
  );
  const notes: Partial<Record<string, FieldNote>> = {};
  for (const row of correctedRows(target.profile, target.corrections) ?? []) {
    if (row.corrected === undefined) continue;
    const key = row.field === "experience" ? "years_of_experience" : row.field;
    notes[key] = {
      extracted: row.corrected.extracted,
      by: names.get(row.corrected.by) ?? "",
      when: format.dateTime(new Date(row.corrected.at), { dateStyle: "medium" }),
    };
  }

  const title =
    target.candidate.name === null
      ? t("titleUnnamed")
      : t("title", { name: target.candidate.name });
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.intro}>{t("intro", { file: target.file.fileName })}</p>
      </header>
      <CorrectionForm
        action={correctProfile.bind(null, {
          lang,
          candidateId,
          fileId: target.file.id,
          back,
        })}
        values={values}
        notes={notes}
        back={back}
      />
    </div>
  );
}
