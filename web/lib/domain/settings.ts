// The settings page (T102). Retention is chosen from the periods the database accepts
// (set_retention, migration 0022); a deletion lookup searches candidates by what identifies them.

/** The select's values: months, or never deleting automatically. */
export const RETENTION_CHOICES = ["6", "12", "24", "never"] as const;

/** Months, null for never, or undefined for anything not offered. */
export function retentionFrom(value: string): number | null | undefined {
  if (value === "never") return null;
  return RETENTION_CHOICES.some((choice) => choice === value) ? Number(value) : undefined;
}

/** Characters a PostgREST filter reads as its own syntax, or a pattern as a wildcard. */
const FILTER_SYNTAX = /[%_,()*\\]/gu;
const MIN_LENGTH = 2;

/** The text to look a candidate up by, safe inside a filter; null when too short to search. */
export function lookupPattern(query: string): string | null {
  const text = query.replace(FILTER_SYNTAX, "").trim();
  return text.length < MIN_LENGTH ? null : text;
}
