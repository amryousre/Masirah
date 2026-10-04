// The quality drop-off (T064): the point in a ranking where scores fall materially, so the
// recruiter knows she can stop reading there. It comes from the distribution, not a fixed rank:
// the widest gap between neighbours, when it stands well clear of the usual spacing.

/** A list this short is read whole; a marker would only add noise. */
export const MIN_RANKED = 5;
/** Points out of 100: a smaller fall is noise in the scoring, never a break. */
export const MIN_GAP = 8;
/** How many times the typical gap the break must be, so an evenly spread list is left unmarked. */
const TYPICAL_TIMES = 3;

export interface DropOff {
  /** How many candidates rank above the break. */
  above: number;
  /** The fall in points across it. */
  gap: number;
}

function median(values: readonly number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1
    ? (sorted[middle] ?? 0)
    : ((sorted[middle - 1] ?? 0) + (sorted[middle] ?? 0)) / 2;
}

export function dropOff(scores: readonly number[]): DropOff | null {
  if (scores.length < MIN_RANKED) return null;
  const ranked = [...scores].sort((a, b) => b - a);
  const gaps = ranked.slice(1).map((score, index) => (ranked[index] ?? score) - score);
  // The first of equal gaps wins: that is where quality first falls.
  const widest = gaps.reduce((best, gap, index) => (gap > (gaps[best] ?? 0) ? index : best), 0);
  const gap = gaps[widest] ?? 0;
  if (gap < MIN_GAP || gap < TYPICAL_TIMES * median(gaps)) return null;
  return { above: widest + 1, gap };
}
