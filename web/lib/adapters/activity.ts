import type { Json } from "./database.types";
import type { SupabaseClient } from "./supabase";

/** What the audit trail records about candidate data (FR-074); decisions are written by the database. */
export type AuditedAction = "candidate.viewed" | "candidate.exported";

/**
 * Writes one audit row as the signed-in member (T099). The activity table takes inserts only, and
 * only for the member's own organisation and in their own name, so the row cannot be written for
 * someone else or changed afterwards. A failed write throws: candidate data is not shown unrecorded.
 */
export async function recordActivity(
  supabase: SupabaseClient,
  actor: { userId: string; organisationId: string },
  action: AuditedAction,
  subject: { type: "candidate"; id: string },
  metadata: Record<string, Json> = {},
): Promise<void> {
  const { error } = await supabase.from("activity").insert({
    organisation_id: actor.organisationId,
    actor_id: actor.userId,
    action,
    subject_type: subject.type,
    subject_id: subject.id,
    metadata,
  });
  if (error) throw new Error(`The audit trail could not record ${action}: ${error.message}`);
}
