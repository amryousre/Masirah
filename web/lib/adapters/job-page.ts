import type { CandidateFigures, Decision, JobFile } from "@/lib/domain/ranking";

import type { SupabaseClient } from "./supabase";

export interface JobHeader {
  id: string;
  title: string;
  location: string | null;
  minimumExperienceYears: number | null;
}

/**
 * A job's page (T063): the job, its candidates from public.job_candidates (migration 0019) and
 * the files uploaded for it. Row level security limits every read to the member's organisation,
 * so another organisation's job reads as missing.
 */
function unreadable(read: string, error: { message: string }): Error {
  return new Error(`The job's page could not read ${read}: ${error.message}`);
}

export async function readJobPage(
  supabase: SupabaseClient,
  jobId: string,
): Promise<{ job: JobHeader; candidates: CandidateFigures[]; files: JobFile[] } | null> {
  const [job, candidates, files] = await Promise.all([
    supabase
      .from("job")
      .select("id, title, location, minimum_experience_years")
      .eq("id", jobId)
      .maybeSingle(),
    supabase
      .from("job_candidates")
      .select(
        "application_id, candidate_id, full_name, total, justification, confidence, decision, decided_by_email, name_normalised, search_text, scored_at, purged_at",
      )
      .eq("job_id", jobId),
    supabase
      .from("cv_file")
      .select("id, original_filename, status, failure_reason, candidate_id")
      .eq("job_id", jobId)
      .order("created_at", { ascending: true }),
  ]);
  // Each checked on its own, so the message names the read that failed and each result narrows.
  if (job.error) throw unreadable("job", job.error);
  if (candidates.error) throw unreadable("job_candidates", candidates.error);
  if (files.error) throw unreadable("cv_file", files.error);
  if (job.data === null) return null;
  return {
    job: {
      id: job.data.id,
      title: job.data.title,
      location: job.data.location,
      minimumExperienceYears: job.data.minimum_experience_years,
    },
    candidates: candidates.data.flatMap((row) =>
      row.application_id === null || row.candidate_id === null || row.decision === null
        ? []
        : [
            {
              applicationId: row.application_id,
              candidateId: row.candidate_id,
              name: row.full_name,
              total: row.total,
              justification: row.justification,
              confidence: row.confidence,
              decision: row.decision satisfies Decision,
              decidedBy: row.decided_by_email,
              nameNormalised: row.name_normalised,
              searchText: row.search_text ?? "",
              scoredAt: row.scored_at,
              purgedAt: row.purged_at,
            },
          ],
    ),
    files: files.data.map((file) => ({
      id: file.id,
      fileName: file.original_filename,
      status: file.status,
      failureReason: file.failure_reason,
      candidateId: file.candidate_id,
    })),
  };
}
