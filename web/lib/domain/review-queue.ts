/**
 * The review queue (T081, FR-011): every CV that was not ranked, with a reason a recruiter can act
 * on. Each kind asks for something different, so none may read like another:
 *
 * - unreadable: no text could be read, as from a scan or a photo before OCR. A clearer copy helps.
 * - unsupportedLanguage: written in a language version 1.0 does not read. A person reads it, or
 *   asks for an Arabic or English CV.
 * - lowConfidence: read, but too little of what was read is in the file to rank it on.
 * - locked, damaged, declined, notProcessed: the file failed, because of a password, because it
 *   is not a readable document, because the reading model would not read it, or for a reason on
 *   our side. Only the last is helped by uploading the same file again.
 * - needsLook: waiting from before reasons were recorded (migration 0023).
 */

export type ReviewKind =
  | "unreadable"
  | "unsupportedLanguage"
  | "lowConfidence"
  | "locked"
  | "damaged"
  | "declined"
  | "notProcessed"
  | "needsLook";

/** The status word beside the reason, one of the document states the interface already names. */
export type ReviewStatus = "needsReview" | "unsupportedLanguage" | "failed";

/** A cv_file row in review or failed, as the adapter reads it. */
export interface ReviewRow {
  id: string;
  fileName: string;
  mimeType: string;
  status: "needs_review" | "failed";
  reviewReason: "no_text" | "unsupported_language" | "low_confidence" | null;
  reviewLanguage: string | null;
  failureReason: string | null;
  /** The candidate the file was read as, when it was read. */
  candidateId: string | null;
  jobId: string | null;
  jobTitle: string | null;
  updatedAt: string;
}

export interface ReviewItem {
  id: string;
  fileName: string;
  mimeType: string;
  kind: ReviewKind;
  status: ReviewStatus;
  /** The language found, as an ISO 639-1 code, for an unsupported language. */
  language: string | null;
  candidateId: string | null;
  jobId: string | null;
  jobTitle: string | null;
  updatedAt: string;
}

const waiting: Record<NonNullable<ReviewRow["reviewReason"]>, ReviewKind> = {
  no_text: "unreadable",
  unsupported_language: "unsupportedLanguage",
  low_confidence: "lowConfidence",
};

/**
 * Why a file failed, from the reason the worker recorded (pipeline worker.py). An unreadable file
 * is reported as "the file cannot be read: …", and a password-protected PDF names itself so
 * (adapters/native_text.py), and a model that would not read it says it declined; anything else
 * went wrong on our side, not in the file.
 */
export type FailureKind = "locked" | "damaged" | "declined" | "notProcessed";

export function failureKind(reason: string): FailureKind {
  if (reason.includes("password-protected")) return "locked";
  if (reason.startsWith("the file cannot be read")) return "damaged";
  if (reason.startsWith("the model declined to read")) return "declined";
  return "notProcessed";
}

export function reviewItem(row: ReviewRow): ReviewItem {
  const kind: ReviewKind =
    row.status === "failed"
      ? failureKind(row.failureReason ?? "")
      : row.reviewReason === null
        ? "needsLook"
        : waiting[row.reviewReason];
  return {
    id: row.id,
    fileName: row.fileName,
    mimeType: row.mimeType,
    kind,
    status:
      row.status === "failed"
        ? "failed"
        : kind === "unsupportedLanguage"
          ? "unsupportedLanguage"
          : "needsReview",
    language: kind === "unsupportedLanguage" ? row.reviewLanguage : null,
    candidateId: row.candidateId,
    jobId: row.jobId,
    jobTitle: row.jobTitle,
    updatedAt: row.updatedAt,
  };
}
