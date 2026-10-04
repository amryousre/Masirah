import { randomUUID } from "node:crypto";

import type { Locale } from "@/i18n/routing";
import {
  type FileRejection,
  checkFile,
  SIGNATURE_BYTES,
  storedFileName,
} from "@/lib/domain/uploads";

import type { SupabaseClient } from "./supabase";

export const CV_BUCKET = "cv-originals";

export type UploadOutcome =
  | { name: string; status: "queued"; cvFileId: string }
  | { name: string; status: "rejected"; reason: FileRejection }
  | { name: string; status: "failed"; cvFileId?: string };

async function sha256(content: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", content);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

/**
 * One uploaded file, end to end (T061): checked, recorded as a cv_file row, stored under the
 * organisation's folder, and queued for the worker. Everything runs as the signed-in member, so
 * row level security and the bucket's policies apply at every step. Nothing waits for
 * extraction (contracts/web-routes.md).
 *
 * The row comes first, so a stored object always has a row to show it. If storing or queueing
 * fails, the row is marked failed with the reason, so the file is visible rather than lost
 * (SC-006).
 */
export async function storeUpload(
  supabase: SupabaseClient,
  organisationId: string,
  file: File,
  jobId: string | null,
  locale: Locale,
): Promise<UploadOutcome> {
  const content = await file.arrayBuffer();
  const check = checkFile(
    file.name,
    file.size,
    new Uint8Array(content, 0, Math.min(SIGNATURE_BYTES, content.byteLength)),
  );
  if (!check.ok) return { name: file.name, status: "rejected", reason: check.reason };

  const cvFileId = randomUUID();
  const storagePath = `organisations/${organisationId}/cv/${cvFileId}/${storedFileName(check.extension)}`;
  const { error: rowError } = await supabase.from("cv_file").insert({
    id: cvFileId,
    organisation_id: organisationId,
    job_id: jobId,
    storage_path: storagePath,
    original_filename: file.name,
    mime_type: check.mime,
    byte_size: file.size,
    content_hash: await sha256(content),
  });
  if (rowError) return { name: file.name, status: "failed" };

  const fail = async (reason: string): Promise<UploadOutcome> => {
    await supabase
      .from("cv_file")
      .update({ status: "failed", failure_reason: reason })
      .eq("id", cvFileId);
    return { name: file.name, status: "failed", cvFileId };
  };

  const { error: storeError } = await supabase.storage
    .from(CV_BUCKET)
    .upload(storagePath, content, { contentType: check.mime, upsert: false });
  if (storeError) return fail("the file could not be stored");

  const { error: queueError } = await supabase.rpc("enqueue_cv_processing", {
    cv_file_id: cvFileId,
    locale,
  });
  if (queueError) return fail("the file could not be queued for reading");

  return { name: file.name, status: "queued", cvFileId };
}
