// A candidate's own page (T065, T066): the score shown as points earned out of each component's
// weight, the summary's lines, and the candidate's place in the job's ranking.

/** The stored component names (pipeline domain/scoring.py COMPONENTS), in display order. */
const COMPONENTS = [
  ["skills_match", "skills"],
  ["experience_relevance", "experience"],
  ["education", "education"],
  ["tenure_stability", "tenure"],
  ["language", "language"],
  ["location", "location"],
] as const;

export type ComponentKey = (typeof COMPONENTS)[number][1];

export interface ScorePart {
  key: ComponentKey;
  earned: number;
  weight: number;
  /** What the rating rests on, in the interface language. */
  evidence: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Each component's rating (0 to 100) scaled to its weight and rounded half up, as the pipeline
 * rounds the total. Null when the stored components or the weights cannot be read: the page then
 * says there is no breakdown rather than showing points nobody computed.
 */
export function scoreParts(components: unknown, weights: unknown): ScorePart[] | null {
  if (!isRecord(components) || !isRecord(weights)) return null;
  const parts: ScorePart[] = [];
  for (const [stored, key] of COMPONENTS) {
    const component = components[stored];
    const weight = weights[stored];
    if (!isRecord(component) || typeof weight !== "number") return null;
    const { rating, evidence } = component;
    if (typeof rating !== "number" || typeof evidence !== "string") return null;
    parts.push({ key, earned: Math.round((rating * weight) / 100), weight, evidence });
  }
  return parts;
}

/** The summary is stored as its three to five lines joined by newlines. */
export function summaryLines(summary: string): string[] {
  return summary
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

export interface Place {
  rank: number;
  of: number;
  previous: string | null;
  next: string | null;
}

/** Where a candidate sits in a ranking already in order, and who is either side. */
export function placeInRanking(
  ranking: readonly { candidateId: string }[],
  candidateId: string,
): Place | null {
  const index = ranking.findIndex((entry) => entry.candidateId === candidateId);
  if (index === -1) return null;
  return {
    rank: index + 1,
    of: ranking.length,
    previous: ranking[index - 1]?.candidateId ?? null,
    next: ranking[index + 1]?.candidateId ?? null,
  };
}

export type ProfileField =
  | "name"
  | "emails"
  | "phones"
  | "location"
  | "experience"
  | "employment"
  | "education"
  | "skills"
  | "languages"
  | "certifications";

export interface ProfileRow {
  field: ProfileField;
  /** One line per entry; empty when the CV did not give the field. */
  values: string[];
}

const SEPARATOR = " · ";

function text(value: unknown): string | null {
  if (typeof value === "string") return value.trim() === "" ? null : value;
  return typeof value === "number" ? String(value) : null;
}

function entries(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function strings(value: unknown): string[] {
  return Array.isArray(value)
    ? value.map(text).filter((item): item is string => item !== null)
    : [];
}

/** "2020 – 2024", or the one end the CV gives. */
function period(start: unknown, end: unknown): string | null {
  const [from, to] = [text(start), text(end)];
  return from !== null && to !== null ? `${from} – ${to}` : (from ?? to);
}

function line(...parts: (string | null)[]): string {
  return parts.filter((part): part is string => part !== null).join(SEPARATOR);
}

/**
 * The extracted profile (pipeline domain/profile.py) as labelled rows, in the order a CV reads.
 * Every field appears, empty when the CV did not give it, so a missing value is visible.
 */
export function profileRows(profile: unknown): ProfileRow[] | null {
  if (!isRecord(profile)) return null;
  const single = (value: unknown) => {
    const one = text(value);
    return one === null ? [] : [one];
  };
  const skills = strings(profile["skills"]);
  return [
    { field: "name", values: single(profile["name"]) },
    { field: "emails", values: strings(profile["emails"]) },
    { field: "phones", values: strings(profile["phones"]) },
    { field: "location", values: single(profile["location"]) },
    { field: "experience", values: single(profile["years_of_experience"]) },
    {
      field: "employment",
      values: entries(profile["employment"]).map((job) =>
        line(text(job["title"]), text(job["employer"]), period(job["start"], job["end"])),
      ),
    },
    {
      field: "education",
      values: entries(profile["education"]).map((study) =>
        line(
          text(study["qualification"]),
          text(study["institution"]),
          period(study["start"], study["end"]),
        ),
      ),
    },
    { field: "skills", values: skills.length === 0 ? [] : [skills.join(", ")] },
    {
      field: "languages",
      values: entries(profile["languages"]).map((spoken) =>
        line(text(spoken["language"]), text(spoken["level"])),
      ),
    },
    {
      field: "certifications",
      values: entries(profile["certifications"]).map((held) =>
        line(text(held["name"]), text(held["issuer"])),
      ),
    },
  ];
}
