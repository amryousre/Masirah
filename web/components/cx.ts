/** Joins class names, skipping the ones a condition switched off. */
export function cx(...names: (string | false | null | undefined)[]): string {
  return names.filter(Boolean).join(" ");
}
