import type { JobSummary } from "@/lib/domain/jobs";

import type { SupabaseClient } from "./supabase";

/**
 * The signed-in member's jobs, most recently active first, from public.job_overview (migration
 * 0017). Row level security limits them to the member's organisation; nothing here filters by it.
 */
export async function listJobs(supabase: SupabaseClient): Promise<JobSummary[]> {
  const { data, error } = await supabase
    .from("job_overview")
    .select(
      "id, title, location, minimum_experience_years, cv_count, ranked_count, processing_count, attention_count, updated_at",
    )
    .order("updated_at", { ascending: false });
  if (error) throw new Error(`The job list could not be read: ${error.message}`);
  return data.flatMap((row) =>
    row.id === null || row.title === null || row.updated_at === null
      ? []
      : [
          {
            id: row.id,
            title: row.title,
            location: row.location,
            minimumExperienceYears: row.minimum_experience_years,
            cvCount: row.cv_count ?? 0,
            rankedCount: row.ranked_count ?? 0,
            processingCount: row.processing_count ?? 0,
            attentionCount: row.attention_count ?? 0,
            updatedAt: row.updated_at,
          },
        ],
  );
}
