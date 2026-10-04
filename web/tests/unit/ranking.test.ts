import { describe, expect, it } from "vitest";

import {
  type CandidateFigures,
  confidenceLevel,
  firstSentence,
  type JobFile,
  rankJob,
} from "@/lib/domain/ranking";

// A job's ranked list (T063): scored candidates in order, then everything not ranked yet, each
// with what is happening to it. Nothing submitted is left out (SC-006).
const candidate = (figures: Partial<CandidateFigures>): CandidateFigures => ({
  applicationId: "a1",
  candidateId: "c1",
  name: "Mona",
  total: 70,
  justification: "Six years at Nile Pharma. SAP daily.",
  confidence: 0.95,
  decision: "undecided",
  decidedBy: null,
  ...figures,
});
const file = (figures: Partial<JobFile>): JobFile => ({
  id: "f1",
  fileName: "cv.pdf",
  status: "queued",
  failureReason: null,
  candidateId: null,
  ...figures,
});

describe("the ranking", () => {
  it("puts the highest score first and numbers from one", () => {
    const entries = rankJob(
      [
        candidate({ applicationId: "low", name: "B", total: 41 }),
        candidate({ applicationId: "high", name: "A", total: 86 }),
      ],
      [],
    );
    expect(entries.map((entry) => entry.kind === "ranked" && [entry.id, entry.rank])).toEqual([
      ["high", 1],
      ["low", 2],
    ]);
  });

  it("orders equal scores by name, so the order is stable", () => {
    const entries = rankJob(
      [
        candidate({ applicationId: "z", name: "Ziad", total: 70 }),
        candidate({ applicationId: "a", name: "Amr", total: 70 }),
      ],
      [],
    );
    expect(entries.map((entry) => entry.id)).toEqual(["a", "z"]);
  });

  it("gives each ranked row the first sentence of its justification", () => {
    const [entry] = rankJob([candidate({})], []);
    expect(entry).toMatchObject({ kind: "ranked", reason: "Six years at Nile Pharma." });
  });

  it("flags a ranked candidate whose extraction was doubtful", () => {
    const [entry] = rankJob([candidate({ confidence: 0.7 })], []);
    expect(entry).toMatchObject({ kind: "ranked", confidence: "low", needsReview: true });
  });

  it("lists a candidate still being scored as not ranked yet", () => {
    expect(rankJob([candidate({ total: null })], [])).toEqual([
      { kind: "processing", id: "a1", label: "Mona" },
    ]);
  });

  it("lists every file still on its way, and why the others stopped", () => {
    const entries = rankJob(
      [],
      [
        file({ id: "q", fileName: "queued.pdf", status: "queued" }),
        file({ id: "x", fileName: "reading.pdf", status: "extracting" }),
        file({ id: "r", fileName: "doubtful.pdf", status: "needs_review" }),
        file({ id: "f", fileName: "locked.pdf", status: "failed", failureReason: "encrypted" }),
      ],
    );
    expect(entries).toEqual([
      { kind: "processing", id: "q", label: "queued.pdf" },
      { kind: "processing", id: "x", label: "reading.pdf" },
      { kind: "review", id: "r", label: "doubtful.pdf" },
      { kind: "failed", id: "f", label: "locked.pdf", reason: "encrypted" },
    ]);
  });

  it("lists a file that was read once, as the candidate it became", () => {
    const entries = rankJob(
      [candidate({ candidateId: "c-mona" })],
      [file({ id: "e", fileName: "done.pdf", status: "extracted", candidateId: "c-mona" })],
    );
    expect(entries.map((entry) => entry.kind)).toEqual(["ranked"]);
  });

  it("keeps a read file in view while its application is missing, so it never vanishes", () => {
    const entries = rankJob(
      [],
      [file({ id: "e", fileName: "done.pdf", status: "extracted", candidateId: "c-lost" })],
    );
    expect(entries).toEqual([{ kind: "processing", id: "e", label: "done.pdf" }]);
  });
});

describe("confidence", () => {
  it.each([
    [0.97, "high"],
    [0.9, "high"],
    [0.85, "medium"],
    [0.8, "medium"],
    [0.79, "low"],
    [null, "low"],
  ] as const)("%s reads as %s", (value, level) => {
    expect(confidenceLevel(value)).toBe(level);
  });
});

describe("the first sentence", () => {
  it.each([
    ["Strong SAP. Short tenures.", "Strong SAP."],
    ["خبرة قوية في SAP. مدد عمل قصيرة.", "خبرة قوية في SAP."],
    ["هل يناسب؟ نعم.", "هل يناسب؟"],
    ["No full stop at all", "No full stop at all"],
    ["Version 2.5 of the tool. Then more.", "Version 2.5 of the tool."],
  ])("of %j is %j", (text, sentence) => {
    expect(firstSentence(text)).toBe(sentence);
  });
});
