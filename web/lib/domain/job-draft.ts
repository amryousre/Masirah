// A job as a recruiter submits it (T059, FR-001): read from the form, trimmed, bounded and
// checked on the server, because the form is input like any other.

/** The six component weights a new job starts with (pipeline domain/scoring.py, FR-014). */
export const DEFAULT_WEIGHTS = {
  skills_match: 30,
  experience_relevance: 25,
  education: 15,
  tenure_stability: 10,
  language: 10,
  location: 10,
} as const;

export const LIMITS = {
  title: 200,
  description: 10_000,
  location: 200,
  skill: 80,
  skills: 30,
  experienceYears: 50,
} as const;

export const LANGUAGE_REQUIREMENTS = ["ar", "en", "both"] as const;
export type LanguageRequirement = (typeof LANGUAGE_REQUIREMENTS)[number];

export interface JobDraft {
  title: string;
  description: string | null;
  requiredSkills: string[];
  preferredSkills: string[];
  minimumExperienceYears: number | null;
  location: string | null;
  languageRequirement: LanguageRequirement | null;
}

export type DraftProblem = "missing" | "tooLong" | "tooMany" | "invalid";
export type DraftErrors = Partial<Record<keyof JobDraft, DraftProblem>>;

export type DraftResult = { ok: true; draft: JobDraft } | { ok: false; errors: DraftErrors };

function texts(form: FormData, name: string): string[] {
  return form.getAll(name).filter((value): value is string => typeof value === "string");
}

function optional(form: FormData, name: string): string | null {
  const value = texts(form, name)[0]?.trim() ?? "";
  return value === "" ? null : value;
}

/** Distinct, non-empty skills in the order given; "React" and "react" are one skill. */
function skills(values: string[], already: readonly string[] = []): string[] {
  const seen = new Set(already.map((skill) => skill.toLocaleLowerCase()));
  const kept: string[] = [];
  for (const value of values) {
    const skill = value.trim();
    const key = skill.toLocaleLowerCase();
    if (skill === "" || seen.has(key)) continue;
    seen.add(key);
    kept.push(skill);
  }
  return kept;
}

export function jobDraftFrom(form: FormData): DraftResult {
  const errors: DraftErrors = {};

  const title = optional(form, "title");
  if (title === null) errors.title = "missing";
  else if (title.length > LIMITS.title) errors.title = "tooLong";

  const description = optional(form, "description");
  if (description !== null && description.length > LIMITS.description) {
    errors.description = "tooLong";
  }

  const location = optional(form, "location");
  if (location !== null && location.length > LIMITS.location) errors.location = "tooLong";

  const requiredSkills = skills(texts(form, "requiredSkills"));
  const preferredSkills = skills(texts(form, "preferredSkills"), requiredSkills);
  for (const [name, list] of [
    ["requiredSkills", requiredSkills],
    ["preferredSkills", preferredSkills],
  ] as const) {
    if (list.length > LIMITS.skills) errors[name] = "tooMany";
    else if (list.some((skill) => skill.length > LIMITS.skill)) errors[name] = "tooLong";
  }

  const years = optional(form, "minimumExperienceYears");
  const minimumExperienceYears = years === null ? null : Number(years);
  if (
    minimumExperienceYears !== null &&
    (!/^\d+$/.test(years ?? "") || minimumExperienceYears > LIMITS.experienceYears)
  ) {
    errors.minimumExperienceYears = "invalid";
  }

  const language = optional(form, "languageRequirement");
  const languageRequirement = LANGUAGE_REQUIREMENTS.find((code) => code === language) ?? null;
  if (language !== null && languageRequirement === null) errors.languageRequirement = "invalid";

  if (Object.keys(errors).length > 0 || title === null) return { ok: false, errors };
  return {
    ok: true,
    draft: {
      title,
      description,
      requiredSkills,
      preferredSkills,
      minimumExperienceYears,
      location,
      languageRequirement,
    },
  };
}
