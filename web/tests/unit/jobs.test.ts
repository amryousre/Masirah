import { describe, expect, it } from "vitest";

import { attention, type JobSummary, rankedShare } from "@/lib/domain/jobs";

// What each row of the job list says about a job's CVs (T058, design-brief.md section 6): how far
// ranking has got, and what, if anything, needs the recruiter.
const job = (counts: Partial<JobSummary>): JobSummary => ({
  id: "j1",
  title: "Senior Accountant",
  location: "Giza",
  minimumExperienceYears: 5,
  cvCount: 42,
  rankedCount: 41,
  processingCount: 0,
  attentionCount: 0,
  updatedAt: "2026-10-04T10:00:00Z",
  ...counts,
});

describe("a job's progress", () => {
  it("is the share of its CVs that are ranked", () => {
    expect(rankedShare(job({ cvCount: 26, rankedCount: 19 }))).toBeCloseTo(19 / 26);
  });

  it("is nothing for a job with no CVs, rather than a division by zero", () => {
    expect(rankedShare(job({ cvCount: 0, rankedCount: 0 }))).toBe(0);
  });

  it("never passes the whole bar", () => {
    expect(rankedShare(job({ cvCount: 3, rankedCount: 4 }))).toBe(1);
  });
});

describe("what a job needs from the recruiter", () => {
  it("asks for files when the job has none", () => {
    expect(attention(job({ cvCount: 0, rankedCount: 0 }))).toEqual({ kind: "no-cvs" });
  });

  it("says what is still being read and what needs a decision", () => {
    expect(attention(job({ processingCount: 3, attentionCount: 4 }))).toEqual({
      kind: "processing",
      processing: 3,
      decisions: 4,
    });
  });

  it("names decisions when nothing is being read", () => {
    expect(attention(job({ attentionCount: 1 }))).toEqual({ kind: "decisions", decisions: 1 });
  });

  it("is nothing when every CV is ranked", () => {
    expect(attention(job({}))).toEqual({ kind: "nothing" });
  });
});
