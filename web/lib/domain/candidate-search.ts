// Sort, filter and search in a job's ranked list (T069, FR-018). Names are compared in the form
// the worker stored (candidate.name_normalised), so Mohamed finds Mohammed and محمد; the extracted
// fields are compared as text folded the same way, so a search works in either language.

import { foldedParts, namePartsNormalised, searchForm } from "./names";
import type { Decision, RankingEntry } from "./ranking";

export type SortKey = "score" | "name" | "recent";

export interface ListView {
  query: string;
  decision: Decision | "all";
  reviewOnly: boolean;
  sort: SortKey;
}

export const DEFAULT_VIEW: ListView = {
  query: "",
  decision: "all",
  reviewOnly: false,
  sort: "score",
};

type Ranked = Extract<RankingEntry, { kind: "ranked" }>;

/** True once the view leaves candidates out; sorting alone leaves everyone in. */
export function isNarrowed(view: ListView): boolean {
  return view.query.trim() !== "" || view.decision !== "all" || view.reviewOnly;
}

/** Every part of the query must match: the start of a name part, or a word in the fields. */
function matches(query: string, nameParts: readonly string[], haystack: string): boolean {
  return foldedParts(query).every((part) => {
    const [form = part] = namePartsNormalised(part);
    return nameParts.some((namePart) => namePart.startsWith(form)) || haystack.includes(part);
  });
}

function rankedMatches(entry: Ranked, query: string): boolean {
  const nameParts =
    entry.nameNormalised === null
      ? namePartsNormalised(entry.name ?? "")
      : entry.nameNormalised.split(" ");
  const haystack = `${searchForm(entry.name ?? "")} ${searchForm(entry.searchText)}`;
  return matches(query, nameParts, haystack);
}

function keep(entry: RankingEntry, view: ListView): boolean {
  const query = view.query.trim();
  if (entry.kind === "ranked") {
    if (view.decision !== "all" && entry.decision !== view.decision) return false;
    if (view.reviewOnly && !entry.needsReview) return false;
    return query === "" || rankedMatches(entry, query);
  }
  // A file not yet ranked has no decision, and needs review only when it is waiting for one.
  if (view.decision !== "all") return false;
  if (view.reviewOnly && entry.kind !== "review") return false;
  return query === "" || matches(query, [], searchForm(entry.label ?? ""));
}

/**
 * The entries the view keeps, ranked ones in the view's order and the rest after them as they
 * came. Each ranked candidate keeps its rank, which is its place by score whatever the sort.
 */
export function viewRanking(
  entries: readonly RankingEntry[],
  view: ListView,
  locale: string,
): RankingEntry[] {
  const kept = entries.filter((entry) => keep(entry, view));
  const ranked = kept.filter((entry): entry is Ranked => entry.kind === "ranked");
  const rest = kept.filter((entry) => entry.kind !== "ranked");
  const collator = new Intl.Collator(locale);
  const order: Record<SortKey, (a: Ranked, b: Ranked) => number> = {
    score: (a, b) => a.rank - b.rank,
    name: (a, b) => collator.compare(a.name ?? "", b.name ?? "") || a.rank - b.rank,
    recent: (a, b) => (b.scoredAt ?? "").localeCompare(a.scoredAt ?? "") || a.rank - b.rank,
  };
  return [...ranked.sort(order[view.sort]), ...rest];
}

const DECISIONS: readonly ListView["decision"][] = ["all", "undecided", "shortlisted", "rejected"];
const SORTS: readonly SortKey[] = ["score", "name", "recent"];

function oneOf<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return allowed.find((item) => item === value) ?? fallback;
}

/** The view kept in the page's address, so going back to the list finds it as it was left. */
export function viewFromParams(params: { get: (name: string) => string | null }): ListView {
  return {
    query: params.get("q") ?? "",
    decision: oneOf(params.get("decision"), DECISIONS, DEFAULT_VIEW.decision),
    reviewOnly: params.get("review") === "1",
    sort: oneOf(params.get("sort"), SORTS, DEFAULT_VIEW.sort),
  };
}

export function paramsFromView(view: ListView): URLSearchParams {
  const params = new URLSearchParams();
  if (view.query !== "") params.set("q", view.query);
  if (view.decision !== DEFAULT_VIEW.decision) params.set("decision", view.decision);
  if (view.reviewOnly) params.set("review", "1");
  if (view.sort !== DEFAULT_VIEW.sort) params.set("sort", view.sort);
  return params;
}
