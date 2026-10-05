import type { Decision } from "@/lib/domain/ranking";
import type { RejectionReason } from "@/lib/domain/decisions";

import type { SupabaseClient } from "./supabase";

export type RecordedDecision =
  | { kind: "recorded"; decision: Decision; decidedBy: string | null; decidedAt: string | null }
  | { kind: "not-found" }
  | { kind: "refused" };

/**
 * Records a decision through record_decision (migration 0021), which names the signed-in member
 * as the decider and writes the audit row. Another organisation's application is not found.
 */
export async function recordDecision(
  supabase: SupabaseClient,
  applicationId: string,
  decision: Decision,
  reason: RejectionReason | null,
): Promise<RecordedDecision> {
  const { data, error } = await supabase
    .rpc("record_decision", {
      target_application: applicationId,
      chosen: decision,
      ...(reason !== null && { reason }),
    })
    .single();
  if (error) {
    if (error.code === "P0002") return { kind: "not-found" };
    if (error.code === "22023" || error.code === "42501") return { kind: "refused" };
    throw new Error(`The decision could not be recorded: ${error.message}`);
  }
  return {
    kind: "recorded",
    decision: data.decision,
    decidedBy: data.decided_by_email,
    decidedAt: data.decided_at,
  };
}
