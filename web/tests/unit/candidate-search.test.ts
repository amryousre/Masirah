import { describe, expect, it } from "vitest";

import {
  DEFAULT_VIEW,
  isNarrowed,
  type ListView,
  paramsFromView,
  viewFromParams,
  viewRanking,
} from "@/lib/domain/candidate-search";
import type { RankingEntry } from "@/lib/domain/ranking";

// Sort, filter and search in a job's ranked list (T069, FR-018): in both languages, across the
// name and the extracted fields, with name spellings folded as the worker folded them.

type Ranked = Extract<RankingEntry, { kind: "ranked" }>;

const ranked = (fields: Partial<Ranked>): Ranked => ({
  kind: "ranked",
  id: "a1",
  candidateId: "c1",
  rank: 1,
  name: "Mona",
  reason: "Reason.",
  score: 70,
  confidence: "high",
  needsReview: false,
  decision: "undecided",
  decidedBy: null,
  nameNormalised: "منى",
  searchText: "",
  scoredAt: "2026-10-01T10:00:00Z",
  ...fields,
});

const mohammed = ranked({
  id: "a-mohammed",
  rank: 1,
  name: "Mohammed Abdel Rahman",
  nameNormalised: "محمد عبدالرحمن",
  score: 86,
  searchText: "Nasr City, Cairo React TypeScript Vodafone Egypt Front-end Engineer",
  scoredAt: "2026-10-01T09:00:00Z",
});
const yasmin = ranked({
  id: "a-yasmin",
  rank: 2,
  name: "ياسمين فاروق",
  nameNormalised: "ياسمين فاروق",
  score: 78,
  searchText: "الجيزة SAP محاسبة جامعة القاهرة",
  decision: "shortlisted",
  decidedBy: "nourhan@example.test",
  scoredAt: "2026-10-03T09:00:00Z",
});
const omar = ranked({
  id: "a-omar",
  rank: 3,
  name: "Omar Hassan",
  nameNormalised: "عمر حسن",
  score: 61,
  searchText: "Alexandria Angular",
  needsReview: true,
  confidence: "low",
  scoredAt: "2026-10-02T09:00:00Z",
});
const reading: RankingEntry = { kind: "processing", id: "f1", label: "Sara_Nabil_CV.pdf" };
const entries: RankingEntry[] = [mohammed, yasmin, omar, reading];

const view = (changes: Partial<ListView>): ListView => ({ ...DEFAULT_VIEW, ...changes });
const ids = (list: readonly RankingEntry[]) => list.map((entry) => entry.id);

describe("search", () => {
  it("finds a name however it is spelled, in either script", () => {
    for (const query of ["Mohamed", "muhammad", "محمد", "مُحَمَّد"]) {
      expect(ids(viewRanking(entries, view({ query }), "en"))).toEqual(["a-mohammed"]);
    }
    expect(ids(viewRanking(entries, view({ query: "Yasmine" }), "en"))).toEqual(["a-yasmin"]);
  });

  it("finds a compound name written apart or together", () => {
    for (const query of ["Abdel Rahman", "abdelrahman", "عبد الرحمن"]) {
      expect(ids(viewRanking(entries, view({ query }), "en"))).toEqual(["a-mohammed"]);
    }
  });

  it("matches a name as it is typed, from the start of a part", () => {
    expect(ids(viewRanking(entries, view({ query: "Has" }), "en"))).toEqual(["a-omar"]);
  });

  it("keeps different names apart", () => {
    expect(ids(viewRanking(entries, view({ query: "Mahmoud" }), "en"))).toEqual([]);
    expect(ids(viewRanking(entries, view({ query: "Hussein" }), "en"))).toEqual([]);
  });

  it("searches the extracted fields, in either language", () => {
    expect(ids(viewRanking(entries, view({ query: "react" }), "en"))).toEqual(["a-mohammed"]);
    expect(ids(viewRanking(entries, view({ query: "sap" }), "en"))).toEqual(["a-yasmin"]);
    expect(ids(viewRanking(entries, view({ query: "القاهره" }), "en"))).toEqual(["a-yasmin"]);
    expect(ids(viewRanking(entries, view({ query: "vodafone" }), "en"))).toEqual(["a-mohammed"]);
  });

  it("needs every word to match, whichever field it is in", () => {
    expect(ids(viewRanking(entries, view({ query: "Omar Alexandria" }), "en"))).toEqual(["a-omar"]);
    expect(ids(viewRanking(entries, view({ query: "Omar React" }), "en"))).toEqual([]);
  });

  it("finds a file still being read by its name", () => {
    expect(ids(viewRanking(entries, view({ query: "sara" }), "en"))).toEqual(["f1"]);
  });

  it("shows everything for an empty or blank search", () => {
    expect(ids(viewRanking(entries, view({ query: "   " }), "en"))).toEqual(ids(entries));
  });
});

describe("filters", () => {
  it("keeps one decision, and leaves out files that have none", () => {
    expect(ids(viewRanking(entries, view({ decision: "shortlisted" }), "en"))).toEqual([
      "a-yasmin",
    ]);
    expect(ids(viewRanking(entries, view({ decision: "undecided" }), "en"))).toEqual([
      "a-mohammed",
      "a-omar",
    ]);
  });

  it("keeps only what needs review", () => {
    const review: RankingEntry = { kind: "review", id: "f2", label: "scan.jpg" };
    expect(ids(viewRanking([...entries, review], view({ reviewOnly: true }), "en"))).toEqual([
      "a-omar",
      "f2",
    ]);
  });
});

describe("sorting", () => {
  it("ranks by score unless asked otherwise, keeping each candidate's rank", () => {
    const sorted = viewRanking(entries, view({ sort: "name" }), "en");
    expect(ids(sorted)).toEqual(["a-mohammed", "a-omar", "a-yasmin", "f1"]);
    expect(sorted.map((entry) => (entry.kind === "ranked" ? entry.rank : null))).toEqual([
      1,
      3,
      2,
      null,
    ]);
  });

  it("puts the most recently scored first", () => {
    expect(ids(viewRanking(entries, view({ sort: "recent" }), "en"))).toEqual([
      "a-yasmin",
      "a-omar",
      "a-mohammed",
      "f1",
    ]);
  });
});

describe("isNarrowed", () => {
  it("is true once anything leaves candidates out", () => {
    expect(isNarrowed(DEFAULT_VIEW)).toBe(false);
    expect(isNarrowed(view({ sort: "name" }))).toBe(false);
    expect(isNarrowed(view({ query: " " }))).toBe(false);
    expect(isNarrowed(view({ query: "sap" }))).toBe(true);
    expect(isNarrowed(view({ decision: "rejected" }))).toBe(true);
    expect(isNarrowed(view({ reviewOnly: true }))).toBe(true);
  });
});

describe("the view in the address", () => {
  it("reads back what it wrote", () => {
    const narrowed = view({
      query: "محمد",
      decision: "shortlisted",
      reviewOnly: true,
      sort: "name",
    });
    expect(viewFromParams(new URLSearchParams(paramsFromView(narrowed)))).toEqual(narrowed);
  });

  it("writes nothing for the default view, so the plain address stays plain", () => {
    expect(paramsFromView(DEFAULT_VIEW).toString()).toBe("");
  });

  it("ignores values it does not know", () => {
    expect(
      viewFromParams(new URLSearchParams("decision=maybe&sort=height&review=perhaps")),
    ).toEqual(DEFAULT_VIEW);
  });
});
