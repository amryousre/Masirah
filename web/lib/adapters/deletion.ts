import type { SupabaseClient } from "./supabase";

export type DeletionRequest =
  { kind: "requested"; requestedAt: string } | { kind: "not-found" } | { kind: "refused" };

/**
 * Asks for a candidate's personal data to be removed (T101, FR-076), through
 * request_candidate_deletion (migration 0022), which records the member and an audit row. Asking
 * again while a request is open returns the first. The worker's next sweep does the removal.
 */
export async function requestDeletion(
  supabase: SupabaseClient,
  candidateId: string,
): Promise<DeletionRequest> {
  const { data, error } = await supabase.rpc("request_candidate_deletion", {
    target_candidate: candidateId,
  });
  if (error) {
    if (error.code === "P0002") return { kind: "not-found" };
    if (error.code === "42501") return { kind: "refused" };
    throw new Error(`The deletion request could not be recorded: ${error.message}`);
  }
  return { kind: "requested", requestedAt: data };
}
