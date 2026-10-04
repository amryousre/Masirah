// A job as the job list shows it (T058): its CVs by state, from public.job_overview.

export interface JobSummary {
  id: string;
  title: string;
  location: string | null;
  minimumExperienceYears: number | null;
  /** CVs uploaded for this job. */
  cvCount: number;
  /** Candidates scored against it. */
  rankedCount: number;
  /** CVs still queued or being read. */
  processingCount: number;
  /** CVs in review or failed: each needs a person to decide what happens. */
  attentionCount: number;
  updatedAt: string;
}

/** How much of the progress bar is filled: the share of the job's CVs that are ranked. */
export function rankedShare(job: JobSummary): number {
  if (job.cvCount === 0) return 0;
  return Math.min(job.rankedCount / job.cvCount, 1);
}

export type JobAttention =
  | { kind: "no-cvs" }
  | { kind: "processing"; processing: number; decisions: number }
  | { kind: "decisions"; decisions: number }
  | { kind: "nothing" };

/** What the job needs from the recruiter, most pressing first. */
export function attention(job: JobSummary): JobAttention {
  if (job.cvCount === 0) return { kind: "no-cvs" };
  if (job.processingCount > 0) {
    return { kind: "processing", processing: job.processingCount, decisions: job.attentionCount };
  }
  if (job.attentionCount > 0) return { kind: "decisions", decisions: job.attentionCount };
  return { kind: "nothing" };
}
