import { type Corrections, correctionsOf, type ProfileKey } from "@/lib/domain/corrections";

import type { Json } from "./database.types";
import type { SupabaseClient } from "./supabase";

export interface CorrectionTarget {
  candidate: { id: string; name: string | null };
  file: { id: string; fileName: string; jobId: string | null };
  /** The profile as extraction wrote it. */
  profile: unknown;
  corrections: Corrections;
}

/**
 * The profile a member corrects (T082): the candidate's CV named by `fileId`, or their latest
 * CV that has been read. Row level security limits the reads to the member's organisation, so
 * another organisation's candidate, or a file that is not theirs, reads as missing.
 */
export async function readCorrectionTarget(
  supabase: SupabaseClient,
  candidateId: string,
  fileId: string | null,
): Promise<CorrectionTarget | null> {
  const [person, files] = await Promise.all([
    supabase
      .from("candidate")
      .select("id, full_name, purged_at")
      .eq("id", candidateId)
      .maybeSingle(),
    supabase
      .from("cv_file")
      .select("id, original_filename, job_id, parsed_profile(profile, field_overrides, is_current)")
      .eq("candidate_id", candidateId)
      .is("purged_at", null)
      .order("created_at", { ascending: false }),
  ]);
  if (person.error) throw new Error(`The candidate could not be read: ${person.error.message}`);
  if (files.error) throw new Error(`The CVs could not be read: ${files.error.message}`);
  if (person.data === null || person.data.purged_at !== null) return null;
  const read = files.data.flatMap((file) => {
    const current = file.parsed_profile.find((profile) => profile.is_current);
    return current === undefined ? [] : [{ file, current }];
  });
  const chosen = fileId === null ? read[0] : read.find(({ file }) => file.id === fileId);
  if (chosen === undefined) return null;
  return {
    candidate: { id: person.data.id, name: person.data.full_name },
    file: {
      id: chosen.file.id,
      fileName: chosen.file.original_filename,
      jobId: chosen.file.job_id,
    },
    profile: chosen.current.profile,
    corrections: correctionsOf(chosen.current.field_overrides),
  };
}

/**
 * Saves corrections through correct_profile (migration 0024), which checks them, keeps who made
 * them and records them on the audit trail. A corrected name comes with its searchable form.
 */
export async function saveCorrections(
  supabase: SupabaseClient,
  fileId: string,
  corrections: Partial<Record<ProfileKey, unknown>>,
  nameNormalised: string | null,
): Promise<void> {
  const { error } = await supabase.rpc("correct_profile", {
    target_file: fileId,
    corrections: corrections as Json,
    ...(nameNormalised === null ? {} : { corrected_name_normalised: nameNormalised }),
  });
  if (error) throw new Error(`The corrections could not be saved: ${error.message}`);
}

/** How the interface names the members who corrected fields: by their email. */
export async function memberNames(
  supabase: SupabaseClient,
  ids: string[],
): Promise<Map<string, string>> {
  if (ids.length === 0) return new Map();
  const { data, error } = await supabase.from("app_user").select("id, email").in("id", ids);
  if (error) throw new Error(`The members could not be read: ${error.message}`);
  return new Map(data.map((member) => [member.id, member.email]));
}
