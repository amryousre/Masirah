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
        "application_id, full_name, total, justification, confidence, decision, decided_by_email",
      )
      .eq("job_id", jobId),
    supabase
      .from("cv_file")
      .select("id, original_filename, status, failure_reason")
      .eq("job_id", jobId)
      .order("created_at", { ascending: true }),
  ]);
  if (job.error || candidates.error || files.error) {
    throw new Error("The job's page could not be read.");
  }
  if (job.data === null) return null;
  return {
    job: {
      id: job.data.id,
      title: job.data.title,
      location: job.data.location,
      minimumExperienceYears: job.data.minimum_experience_years,
    },
    candidates: candidates.data.flatMap((row) =>
      row.application_id === null || row.decision === null
        ? []
        : [
            {
              applicationId: row.application_id,
              name: row.full_name,
              total: row.total,
              justification: row.justification,
              confidence: row.confidence,
              decision: row.decision satisfies Decision,
              decidedBy: row.decided_by_email,
            },
          ],
    ),
    files: files.data.map((file) => ({
      id: file.id,
      fileName: file.original_filename,
      status: file.status,
      failureReason: file.failure_reason,
    })),
  };
}
