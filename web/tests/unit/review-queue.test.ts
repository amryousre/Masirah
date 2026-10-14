import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { failureKind, reviewItem, type ReviewRow } from "@/lib/domain/review-queue";

// The review queue (T081): every CV that was not ranked, each with a reason the recruiter can act
// on. A file with nothing to read and a CV in an unsupported language must never look alike.

const row = (overrides: Partial<ReviewRow>): ReviewRow => ({
  id: "f1",
  fileName: "cv.pdf",
  mimeType: "application/pdf",
  status: "needs_review",
  reviewReason: null,
  reviewLanguage: null,
  failureReason: null,
  candidateId: null,
  jobId: "j1",
  jobTitle: "Accountant",
  updatedAt: "2026-10-06T12:00:00Z",
  ...overrides,
});

describe("reviewItem", () => {
  it("tells a file with nothing to read from a CV in another language", () => {
    const scan = reviewItem(row({ reviewReason: "no_text" }));
    const french = reviewItem(row({ reviewReason: "unsupported_language", reviewLanguage: "fr" }));
    expect([scan.kind, scan.status]).toEqual(["unreadable", "needsReview"]);
    expect([french.kind, french.status, french.language]).toEqual([
      "unsupportedLanguage",
      "unsupportedLanguage",
      "fr",
    ]);
  });

  it("keeps a doubtful extraction apart from both", () => {
    expect(reviewItem(row({ reviewReason: "low_confidence" })).kind).toBe("lowConfidence");
  });

  it("still lists a file that waited before reasons were recorded", () => {
    expect(reviewItem(row({ reviewReason: null })).kind).toBe("needsLook");
  });

  it("names why a file failed", () => {
    const failed = reviewItem(
      row({
        status: "failed",
        failureReason: "the file cannot be read: the PDF is password-protected",
      }),
    );
    expect([failed.kind, failed.status]).toEqual(["locked", "failed"]);
  });

  it("carries what the page needs to show the file and its job", () => {
    const item = reviewItem(row({ jobId: null, jobTitle: null }));
    expect(item).toMatchObject({ id: "f1", fileName: "cv.pdf", jobId: null, jobTitle: null });
  });
});

describe("failureKind", () => {
  it("reads the worker's reasons", () => {
    expect(failureKind("the file cannot be read: the PDF is password-protected")).toBe("locked");
    expect(failureKind("the file cannot be read: the PDF cannot be read: No /Root object!")).toBe(
      "damaged",
    );
    expect(failureKind("the file cannot be read: the file is neither a PDF nor a DOCX")).toBe(
      "damaged",
    );
    expect(failureKind("processing failed after 5 attempts")).toBe("notProcessed");
    expect(failureKind("the original file is missing from storage")).toBe("notProcessed");
  });

  it("tells a model's refusal from a fault of ours: uploading the same file again won't help", () => {
    expect(failureKind("the model declined to read the CV: refused")).toBe("declined");
    expect(failureKind("the model declined to read the scan: refused")).toBe("declined");
  });

  // The worker records its reasons as text. Until they are a structured column, the phrases matched
  // above are held to the pipeline's source, so rewording one there fails here rather than quietly
  // telling recruiters every failure is ours.
  it.each([
    ["adapters/native_text.py", "the PDF is password-protected"],
    ["worker.py", 'f"the file cannot be read: {error}"'],
    ["worker.py", 'f"the model declined to read the CV: {error}"'],
    ["worker.py", 'f"the model declined to read the scan: {error}"'],
  ])("the pipeline's %s still says %s", (file, phrase) => {
    const source = readFileSync(
      path.resolve(import.meta.dirname, "../../../pipeline/src/masirah_pipeline", file),
      "utf8",
    );
    expect(source).toContain(phrase);
  });
});
