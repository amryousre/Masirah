// Shortlisting and rejecting (T090, FR-023). The score is advice; a decision is a person's, and the
// request never says whose: record_decision (migration 0021) takes the decider from the session.

import type { Decision } from "./ranking";

/** Why a candidate was rejected, as the reject dialog lists them (the database checks the same). */
export const REJECTION_REASONS = ["experience", "skills", "location", "other"] as const;
export type RejectionReason = (typeof REJECTION_REASONS)[number];

const DECISIONS: readonly Decision[] = ["undecided", "shortlisted", "rejected"];

export type DecisionRequest =
  | { ok: true; decision: Decision; reason: RejectionReason | null }
  | { ok: false; error: "decision" | "reason" };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function decisionRequest(body: unknown): DecisionRequest {
  if (!isRecord(body)) return { ok: false, error: "decision" };
  const decision = DECISIONS.find((known) => known === body["decision"]);
  if (decision === undefined) return { ok: false, error: "decision" };
  const given = body["reason"];
  if (decision !== "rejected") {
    return given === undefined || given === null
      ? { ok: true, decision, reason: null }
      : { ok: false, error: "reason" };
  }
  const reason = REJECTION_REASONS.find((known) => known === given);
  return reason === undefined ? { ok: false, error: "reason" } : { ok: true, decision, reason };
}
