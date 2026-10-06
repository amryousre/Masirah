import { type ProfileField, type ProfileRow, profileRows } from "./candidate";

/**
 * Correcting an extracted field (T082, T083, FR-010). A correction is kept beside the machine's
 * value in parsed_profile.field_overrides (migration 0024), so the profile shown is the extraction
 * with each correction in its place, and a corrected row says what was read and who changed it.
 */

/** The profile's fields as extraction writes them (pipeline domain/profile.py). */
export const PROFILE_KEYS = [
  "name",
  "emails",
  "phones",
  "location",
  "years_of_experience",
  "employment",
  "education",
  "skills",
  "languages",
  "certifications",
] as const;
export type ProfileKey = (typeof PROFILE_KEYS)[number];

/** The parts of each kind of entry, in the order the form shows them. */
export const ENTRY_PARTS = {
  employment: ["title", "employer", "start", "end"],
  education: ["qualification", "institution", "start", "end"],
  languages: ["language", "level"],
  certifications: ["name", "issuer"],
} as const;
export type EntryKey = keyof typeof ENTRY_PARTS;

const DATED: readonly EntryKey[] = ["employment", "education"];

export interface Correction {
  value: unknown;
  /** The member who made it. */
  by: string;
  at: string;
}
export type Corrections = Partial<Record<ProfileKey, Correction>>;

export type CorrectionError = "email" | "years" | "date";
export type FormResult =
  | { ok: true; corrections: Partial<Record<ProfileKey, unknown>> }
  | { ok: false; errors: Partial<Record<ProfileKey, CorrectionError>> };

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const DATE = /^(\d{4}(-(0[1-9]|1[0-2]))?|present)$/;
const MAX_YEARS = 60;
/** What a recruiter may write for a job or study still going on, stored as extraction stores it. */
const PRESENT = new Set(["present", "now", "حتى الآن", "الآن", "حاليا", "حاليًا"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isProfileKey(key: string): key is ProfileKey {
  return (PROFILE_KEYS as readonly string[]).includes(key);
}

/** The corrections stored for a profile, keeping only well-formed ones of known fields. */
export function correctionsOf(raw: unknown): Corrections {
  if (!isRecord(raw)) return {};
  const corrections: Corrections = {};
  for (const [key, entry] of Object.entries(raw)) {
    if (!isProfileKey(key) || !isRecord(entry)) continue;
    const { by, at } = entry;
    if (!("value" in entry) || typeof by !== "string" || typeof at !== "string") continue;
    corrections[key] = { value: entry["value"], by, at };
  }
  return corrections;
}

/** The extraction with each correction in place of the value it corrects. */
export function correctedProfile(
  profile: unknown,
  corrections: Corrections,
): Record<string, unknown> {
  const base = isRecord(profile) ? profile : {};
  const corrected: Record<string, unknown> = { ...base };
  for (const key of PROFILE_KEYS) {
    const correction = corrections[key];
    if (correction !== undefined) corrected[key] = correction.value;
  }
  return corrected;
}

const keyOfField: Record<ProfileField, ProfileKey> = {
  name: "name",
  emails: "emails",
  phones: "phones",
  location: "location",
  experience: "years_of_experience",
  employment: "employment",
  education: "education",
  skills: "skills",
  languages: "languages",
  certifications: "certifications",
};

export type CorrectedRow = ProfileRow & {
  /** Present when a person corrected the field: what extraction read, who and when. */
  corrected?: { extracted: string[]; by: string; at: string };
};

/** The profile's rows as corrected, each corrected row with what was extracted beside it. */
export function correctedRows(profile: unknown, corrections: Corrections): CorrectedRow[] | null {
  const extracted = profileRows(profile);
  const shown = profileRows(correctedProfile(profile, corrections));
  if (extracted === null || shown === null) return null;
  return shown.map((row, index) => {
    const correction = corrections[keyOfField[row.field]];
    if (correction === undefined) return row;
    return {
      ...row,
      corrected: {
        extracted: extracted[index]?.values ?? [],
        by: correction.by,
        at: correction.at,
      },
    };
  });
}

function scalar(value: string | undefined): string | null {
  const trimmed = (value ?? "").trim();
  return trimmed === "" ? null : trimmed;
}

function lines(value: string | undefined): string[] {
  return (value ?? "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line !== "");
}

/** Entries from "employment.0.title" style fields, in index order, dropping blank ones. */
function entries(key: EntryKey, fields: Map<string, string>): Record<string, string | null>[] {
  const indexes = new Set<number>();
  for (const name of fields.keys()) {
    const match = new RegExp(`^${key}\\.(\\d+)\\.`).exec(name);
    if (match?.[1] !== undefined) indexes.add(Number(match[1]));
  }
  return [...indexes]
    .sort((a, b) => a - b)
    .map((index) =>
      Object.fromEntries(
        ENTRY_PARTS[key].map((part) => {
          const value = scalar(fields.get(`${key}.${String(index)}.${part}`));
          const dated = part === "start" || part === "end";
          return [
            part,
            dated && value !== null && PRESENT.has(value.toLowerCase()) ? "present" : value,
          ];
        }),
      ),
    )
    .filter((entry) => Object.values(entry).some((part) => part !== null));
}

/** Whether two JSON values are the same, whatever the order of an object's keys. */
function same(a: unknown, b: unknown): boolean {
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((item, index) => same(item, b[index]));
  }
  if (isRecord(a) && isRecord(b)) {
    const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
    return [...keys].every((key) => same(a[key] ?? null, b[key] ?? null));
  }
  return (a ?? null) === (b ?? null);
}

/**
 * What a submitted correction form changes: each field whose value differs from the profile as
 * currently corrected, in the shape extraction gives it. A field set back to the extracted value
 * is sent too, which removes its correction. Nothing is sent when anything is invalid.
 */
export function correctionsFromForm(
  submitted: Iterable<[string, string]>,
  profile: unknown,
  corrections: Corrections,
): FormResult {
  const fields = new Map(submitted);
  const errors: Partial<Record<ProfileKey, CorrectionError>> = {};
  const values: Record<ProfileKey, unknown> = {
    name: scalar(fields.get("name")),
    location: scalar(fields.get("location")),
    years_of_experience: null,
    emails: lines(fields.get("emails")),
    phones: lines(fields.get("phones")),
    skills: lines(fields.get("skills")),
    employment: entries("employment", fields),
    education: entries("education", fields),
    languages: entries("languages", fields),
    certifications: entries("certifications", fields),
  };

  const years = scalar(fields.get("years_of_experience"));
  if (years !== null) {
    const number = Number(years);
    if (!/^\d+$/.test(years) || number > MAX_YEARS) errors.years_of_experience = "years";
    else values.years_of_experience = number;
  }
  if ((values.emails as string[]).some((email) => !EMAIL.test(email))) errors.emails = "email";
  for (const key of DATED) {
    const dates = (values[key] as Record<string, string | null>[]).flatMap((entry) => [
      entry["start"],
      entry["end"],
    ]);
    if (dates.some((date) => date != null && !DATE.test(date))) errors[key] = "date";
  }
  if (Object.keys(errors).length > 0) return { ok: false, errors };

  const current = correctedProfile(profile, corrections);
  const changed: Partial<Record<ProfileKey, unknown>> = {};
  for (const key of PROFILE_KEYS) {
    if (!same(values[key], current[key])) changed[key] = values[key];
  }
  return { ok: true, corrections: changed };
}
