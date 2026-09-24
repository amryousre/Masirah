/**
 * The queue message contract (specs/001-phase1-core-screening/contracts/queue-message.md), the
 * only runtime coupling between this application and the pipeline worker. The web application
 * produces these messages; the worker refuses any schema_version it does not recognise.
 */

export const SCHEMA_VERSION = 1;

export const QUEUES = {
  cvProcessing: "cv_processing",
  cvRescoring: "cv_rescoring",
} as const;

export type Locale = "ar" | "en";

export interface CvProcessingMessage {
  readonly schema_version: typeof SCHEMA_VERSION;
  readonly job_type: typeof QUEUES.cvProcessing;
  readonly organisation_id: string;
  readonly cv_file_id: string;
  readonly job_id: string | null;
  readonly content_hash: string;
  readonly storage_path: string;
  readonly locale: Locale;
  readonly enqueued_at: string;
}

export interface CvRescoringMessage {
  readonly schema_version: typeof SCHEMA_VERSION;
  readonly job_type: typeof QUEUES.cvRescoring;
  readonly organisation_id: string;
  readonly application_id: string;
  readonly weights_hash: string;
  readonly locale: Locale;
  readonly enqueued_at: string;
}

export type QueueMessage = CvProcessingMessage | CvRescoringMessage;

export interface CvProcessingInput {
  organisationId: string;
  cvFileId: string;
  jobId: string | null;
  contentHash: string;
  storagePath: string;
  locale: Locale;
  enqueuedAt: Date;
}

export interface CvRescoringInput {
  organisationId: string;
  applicationId: string;
  weightsHash: string;
  locale: Locale;
  enqueuedAt: Date;
}

/** Every segment below the folder must name something: no empty, "." or ".." segment. */
function isFileInside(path: string, folder: string): boolean {
  if (!path.startsWith(folder) || path.includes("\\")) return false;
  return path
    .slice(folder.length)
    .split("/")
    .every((segment) => segment !== "" && segment !== "." && segment !== "..");
}

/** A file outside its own tenant folder is a producer bug, refused before it reaches a queue. */
export function cvProcessingMessage(input: CvProcessingInput): CvProcessingMessage {
  const folder = `organisations/${input.organisationId}/cv/${input.cvFileId}/`;
  if (!isFileInside(input.storagePath, folder)) {
    throw new Error(`storage_path is not a file inside ${folder}`);
  }
  return {
    schema_version: SCHEMA_VERSION,
    job_type: QUEUES.cvProcessing,
    organisation_id: input.organisationId,
    cv_file_id: input.cvFileId,
    job_id: input.jobId,
    content_hash: input.contentHash,
    storage_path: input.storagePath,
    locale: input.locale,
    enqueued_at: input.enqueuedAt.toISOString(),
  };
}

export function cvRescoringMessage(input: CvRescoringInput): CvRescoringMessage {
  return {
    schema_version: SCHEMA_VERSION,
    job_type: QUEUES.cvRescoring,
    organisation_id: input.organisationId,
    application_id: input.applicationId,
    weights_hash: input.weightsHash,
    locale: input.locale,
    enqueued_at: input.enqueuedAt.toISOString(),
  };
}
