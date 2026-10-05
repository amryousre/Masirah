import { describe, expect, it } from "vitest";

import { decisionRequest, REJECTION_REASONS } from "@/lib/domain/decisions";

// What POST /api/applications/{id}/decision accepts (T090): a decision, and for a rejection one of
// the listed reasons. Who decides is never in the request; the database takes it from the session.

describe("decisionRequest", () => {
  it("accepts a shortlist, and the undoing of a decision, without a reason", () => {
    expect(decisionRequest({ decision: "shortlisted" })).toEqual({
      ok: true,
      decision: "shortlisted",
      reason: null,
    });
    expect(decisionRequest({ decision: "undecided" })).toEqual({
      ok: true,
      decision: "undecided",
      reason: null,
    });
  });

  it("accepts a rejection with one of the listed reasons", () => {
    for (const reason of REJECTION_REASONS) {
      expect(decisionRequest({ decision: "rejected", reason })).toEqual({
        ok: true,
        decision: "rejected",
        reason,
      });
    }
  });

  it("refuses a rejection without a listed reason", () => {
    expect(decisionRequest({ decision: "rejected" })).toEqual({ ok: false, error: "reason" });
    expect(decisionRequest({ decision: "rejected", reason: "age" })).toEqual({
      ok: false,
      error: "reason",
    });
  });

  it("refuses a reason on anything but a rejection", () => {
    expect(decisionRequest({ decision: "shortlisted", reason: "skills" })).toEqual({
      ok: false,
      error: "reason",
    });
  });

  it("refuses anything that is not a decision", () => {
    for (const body of [null, "rejected", {}, { decision: "hired" }, { decision: 1 }]) {
      expect(decisionRequest(body)).toEqual({ ok: false, error: "decision" });
    }
  });

  it("ignores a decider named in the request", () => {
    expect(decisionRequest({ decision: "shortlisted", decidedBy: "someone-else" })).toEqual({
      ok: true,
      decision: "shortlisted",
      reason: null,
    });
  });
});
