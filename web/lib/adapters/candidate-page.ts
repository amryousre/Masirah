import type { Decision } from "@/lib/domain/ranking";

import { readJobPage } from "./job-page";
import type { SupabaseClient } from "./supabase";

export interface CandidateScore {
  total: number;
  components: unknown;
  justification: string;
  summary: string;
}

export interface CandidateDocument {
  fileName: string;
  mimeType: string;
  storagePath: string;
}

export interface CandidatePage {
  job: { id: string; title: string; weights: unknown };
  /** The job's whole page, for the candidate's place in its ranking. */
  ranking: NonNullable<Awaited<ReturnType<typeof readJobPage>>>;
  candidate: { id: string; name: string | null };
  decision: { kind: Decision; by: string | null };
  /** Null until the candidate has been scored for the job. */
  score: CandidateScore | null;
  /** The current extraction of the candidate's latest CV, if one was read. */
  profile: { values: unknown; confidence: number } | null;
  document: CandidateDocument | null;
}

function unreadable(read: string, error: { message: string }): Error {
  return new Error(`The candidate's page could not read ${read}: ${error.message}`);
}

/**
 * One candidate's page within a job (T066): their score for the job with its components, the
 * written reasoning and summary, the extracted profile and the original document. Row level
 * security limits each read to the member's organisation, so another organisation's candidate,
 * or one who never applied to this job, reads as missing.
 */
export async function readCandidatePage(
  supabase: SupabaseClient,
  jobId: string,
  candidateId: string,
): Promise<CandidatePage | null> {
  const [ranking, job, application, file] = await Promise.all([
    readJobPage(supabase, jobId),
    supabase.from("job").select("id, title, weights").eq("id", jobId).maybeSingle(),
    supabase
      .from("job_candidates")
      .select("application_id, full_name, decision, decided_by_email")
      .eq("job_id", jobId)
      .eq("candidate_id", candidateId)
      .maybeSingle(),
    supabase
      .from("cv_file")
      .select("id, original_filename, mime_type, storage_path")
      .eq("candidate_id", candidateId)
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle(),
  ]);
  if (job.error) throw unreadable("job", job.error);
  if (application.error) throw unreadable("job_candidates", application.error);
  if (file.error) throw unreadable("cv_file", file.error);
  if (ranking === null || job.data === null) return null;
  const applied = application.data;
  if (applied?.application_id == null || applied.decision === null) return null;

  const [score, profile] = await Promise.all([
    supabase
      .from("score")
      .select("total, components, justification, summary")
      .eq("application_id", applied.application_id)
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle(),
    file.data === null
      ? Promise.resolve({ data: null, error: null })
      : supabase
          .from("parsed_profile")
          .select("profile, confidence")
          .eq("cv_file_id", file.data.id)
          .eq("is_current", true)
          .maybeSingle(),
  ]);
  if (score.error) throw unreadable("score", score.error);
  if (profile.error) throw unreadable("parsed_profile", profile.error);

  return {
    job: { id: job.data.id, title: job.data.title, weights: job.data.weights },
    ranking,
    candidate: { id: candidateId, name: applied.full_name },
    decision: { kind: applied.decision, by: applied.decided_by_email },
    score: score.data,
    profile:
      profile.data === null
        ? null
        : { values: profile.data.profile, confidence: profile.data.confidence },
    document:
      file.data === null
        ? null
        : {
            fileName: file.data.original_filename,
            mimeType: file.data.mime_type,
            storagePath: file.data.storage_path,
          },
  };
}
