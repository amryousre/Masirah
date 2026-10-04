// A job's ranked list (T063): scored candidates in order, then everything not ranked yet. Every
// file submitted for the job appears somewhere, with what is happening to it (SC-006).

/** Below this a profile went to review (pipeline domain/confidence.py THRESHOLD). */
export const REVIEW_BELOW = 0.8;
const HIGH_FROM = 0.9;

export type ConfidenceLevel = "high" | "medium" | "low";
export type Decision = "undecided" | "shortlisted" | "rejected";

/** A row of public.job_candidates: one application to the job. */
export interface CandidateFigures {
  applicationId: string;
  candidateId: string;
  name: string | null;
  /** Null until the candidate has been scored. */
  total: number | null;
  justification: string | null;
  confidence: number | null;
  decision: Decision;
  decidedBy: string | null;
  /** The worker's folded name, null until it has one (T069). */
  nameNormalised: string | null;
  /** The extracted fields search compares. */
  searchText: string;
  scoredAt: string | null;
}

/** A CV uploaded for the job (cv_file with job_id). */
export interface JobFile {
  id: string;
  fileName: string;
  status: "queued" | "extracting" | "extracted" | "needs_review" | "failed";
  failureReason: string | null;
  /** Set once the file has been read into a candidate. */
  candidateId: string | null;
}

export type RankingEntry =
  | {
      kind: "ranked";
      id: string;
      candidateId: string;
      rank: number;
      name: string | null;
      reason: string;
      score: number;
      confidence: ConfidenceLevel;
      needsReview: boolean;
      decision: Decision;
      decidedBy: string | null;
      nameNormalised: string | null;
      searchText: string;
      scoredAt: string | null;
    }
  | { kind: "processing"; id: string; label: string | null }
  | { kind: "review"; id: string; label: string }
  | { kind: "failed"; id: string; label: string; reason: string | null };

export function confidenceLevel(confidence: number | null): ConfidenceLevel {
  if (confidence === null || confidence < REVIEW_BELOW) return "low";
  return confidence >= HIGH_FROM ? "high" : "medium";
}

/** The justification's first sentence: what the list shows of why a candidate ranks there. */
export function firstSentence(text: string): string {
  const end = /[.!?؟](?=\s|$)/u.exec(text);
  return (end === null ? text : text.slice(0, end.index + 1)).trim();
}

export function rankJob(
  candidates: readonly CandidateFigures[],
  files: readonly JobFile[],
): RankingEntry[] {
  const scored = candidates
    .filter(
      (candidate): candidate is CandidateFigures & { total: number } => candidate.total !== null,
    )
    .sort(
      (a, b) =>
        b.total - a.total ||
        (a.name ?? "").localeCompare(b.name ?? "") ||
        a.applicationId.localeCompare(b.applicationId),
    );
  const ranked: RankingEntry[] = scored.map((candidate, index) => ({
    kind: "ranked",
    id: candidate.applicationId,
    candidateId: candidate.candidateId,
    rank: index + 1,
    name: candidate.name,
    reason: firstSentence(candidate.justification ?? ""),
    score: candidate.total,
    confidence: confidenceLevel(candidate.confidence),
    needsReview: candidate.confidence === null || candidate.confidence < REVIEW_BELOW,
    decision: candidate.decision,
    decidedBy: candidate.decidedBy,
    nameNormalised: candidate.nameNormalised,
    searchText: candidate.searchText,
    scoredAt: candidate.scoredAt,
  }));
  const scoring: RankingEntry[] = candidates
    .filter((candidate) => candidate.total === null)
    .map((candidate) => ({
      kind: "processing",
      id: candidate.applicationId,
      label: candidate.name,
    }));
  // A file that was read became a candidate above, unless its application was never made (the
  // worker gave up after it committed the extraction); that file stays listed, never vanishes.
  const applied = new Set(candidates.map((candidate) => candidate.candidateId));
  const waiting: RankingEntry[] = files.flatMap((file): RankingEntry[] => {
    switch (file.status) {
      case "queued":
      case "extracting":
        return [{ kind: "processing", id: file.id, label: file.fileName }];
      case "needs_review":
        return [{ kind: "review", id: file.id, label: file.fileName }];
      case "failed":
        return [{ kind: "failed", id: file.id, label: file.fileName, reason: file.failureReason }];
      case "extracted":
        return file.candidateId !== null && applied.has(file.candidateId)
          ? []
          : [{ kind: "processing", id: file.id, label: file.fileName }];
    }
  });
  return [...ranked, ...scoring, ...waiting];
}
