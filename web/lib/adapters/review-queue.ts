import { reviewItem, type ReviewItem } from "@/lib/domain/review-queue";

import type { SupabaseClient } from "./supabase";

const IN_QUEUE = ["needs_review", "failed"] as const;

/**
 * The organisation's review queue, most recently changed first (T081). Row level security limits
 * it to the member's organisation. A file whose personal data was purged has nothing left to
 * review, so it is not listed.
 */
export async function listReviewQueue(supabase: SupabaseClient): Promise<ReviewItem[]> {
  const { data, error } = await supabase
    .from("cv_file")
    .select(
      "id, original_filename, mime_type, status, review_reason, review_language, failure_reason, job_id, updated_at, job:job!cv_file_job_in_same_organisation(title)",
    )
    .in("status", IN_QUEUE)
    .is("purged_at", null)
    .order("updated_at", { ascending: false });
  if (error) throw new Error(`The review queue could not be read: ${error.message}`);
  return data.map((row) =>
    reviewItem({
      id: row.id,
      fileName: row.original_filename,
      mimeType: row.mime_type,
      status: row.status as "needs_review" | "failed",
      reviewReason: row.review_reason,
      reviewLanguage: row.review_language,
      failureReason: row.failure_reason,
      jobId: row.job_id,
      jobTitle: row.job?.title ?? null,
      updatedAt: row.updated_at,
    }),
  );
}

/** How many files wait in the queue, for the count beside its link. */
export async function countReviewQueue(supabase: SupabaseClient): Promise<number> {
  const { count, error } = await supabase
    .from("cv_file")
    .select("id", { count: "exact", head: true })
    .in("status", IN_QUEUE)
    .is("purged_at", null);
  if (error) throw new Error(`The review queue could not be counted: ${error.message}`);
  return count ?? 0;
}

/** Where a file in the queue is stored, or null when it is not in the queue or not the member's. */
export async function reviewOriginal(
  supabase: SupabaseClient,
  cvFileId: string,
): Promise<{ storagePath: string; fileName: string } | null> {
  const { data, error } = await supabase
    .from("cv_file")
    .select("storage_path, original_filename")
    .eq("id", cvFileId)
    .in("status", IN_QUEUE)
    .is("purged_at", null)
    .maybeSingle();
  if (error) throw new Error(`The file could not be read: ${error.message}`);
  return data === null
    ? null
    : { storagePath: data.storage_path, fileName: data.original_filename };
}
