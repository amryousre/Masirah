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
  decision: { applicationId: string; kind: Decision; by: string | null; at: string | null };
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
 * written reasoning and summary, and the CV sent for the job with its extraction, so the document
 * and the profile beside it are always the same file's. Row level security limits each read to
 * the member's organisation, so another organisation's candidate, or one who never applied to
 * this job, reads as missing.
 */
export async function readCandidatePage(
  supabase: SupabaseClient,
  jobId: string,
  candidateId: string,
): Promise<CandidatePage | null> {
  const [ranking, job, application, files] = await Promise.all([
    readJobPage(supabase, jobId),
    supabase.from("job").select("id, title, weights").eq("id", jobId).maybeSingle(),
    supabase
      .from("job_candidates")
      .select("application_id, full_name, decision, decided_by_email, decided_at")
      .eq("job_id", jobId)
      .eq("candidate_id", candidateId)
      .maybeSingle(),
    supabase
      .from("cv_file")
      .select("id, original_filename, mime_type, storage_path, job_id")
      .eq("candidate_id", candidateId)
      .order("created_at", { ascending: false }),
  ]);
  if (job.error) throw unreadable("job", job.error);
  if (application.error) throw unreadable("job_candidates", application.error);
  if (files.error) throw unreadable("cv_file", files.error);
  // The CV sent for this job, beside this job's score. A file uploaded before files carried their
  // job (migration 0017) has none; the latest such file stands in. A CV sent for another job never
  // does: its document and extraction would sit beside a score they did not produce.
  const file =
    files.data.find((candidateFile) => candidateFile.job_id === jobId) ??
    files.data.find((candidateFile) => candidateFile.job_id === null) ??
    null;
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
    file === null
      ? Promise.resolve({ data: null, error: null })
      : supabase
          .from("parsed_profile")
          .select("profile, confidence")
          .eq("cv_file_id", file.id)
          .eq("is_current", true)
          .maybeSingle(),
  ]);
  if (score.error) throw unreadable("score", score.error);
  if (profile.error) throw unreadable("parsed_profile", profile.error);

  return {
    job: { id: job.data.id, title: job.data.title, weights: job.data.weights },
    ranking,
    candidate: { id: candidateId, name: applied.full_name },
    decision: {
      applicationId: applied.application_id,
      kind: applied.decision,
      by: applied.decided_by_email,
      at: applied.decided_at,
    },
    score: score.data,
    profile:
      profile.data === null
        ? null
        : { values: profile.data.profile, confidence: profile.data.confidence },
    document:
      file === null
        ? null
        : {
            fileName: file.original_filename,
            mimeType: file.mime_type,
            storagePath: file.storage_path,
          },
  };
}
