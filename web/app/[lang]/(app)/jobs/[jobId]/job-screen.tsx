"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/button/button";
import { CandidateFilters } from "@/components/candidates/candidate-filters";
import { type CandidateRow, CandidateTable } from "@/components/candidates/candidate-table";
import { DropZone, type UploadItem, UploadList } from "@/components/upload/upload";
import {
  DEFAULT_VIEW,
  isNarrowed,
  type ListView,
  paramsFromView,
  viewFromParams,
  viewRanking,
} from "@/lib/domain/candidate-search";
import type { DropOff } from "@/lib/domain/drop-off";
import type { RankingEntry } from "@/lib/domain/ranking";

import styles from "./job.module.css";

interface UploadOutcome {
  name: string;
  /** pending: stored, and queued again by the worker's reconciliation within minutes. */
  status: "queued" | "pending" | "rejected" | "failed";
  reason?: "type" | "size" | "empty";
}

/**
 * The job's working area (T062, T063). Dropping files navigates nowhere: the files appear with
 * their progress, and the ranked list below fills in as the worker reads them (design-brief.md
 * section 5). The list is the server's; refreshing re-reads it after each batch. Search, filters
 * and sort (T069) work on the list in the page and live in its address, so going back from a
 * candidate finds the list as it was left.
 */
export function JobScreen({
  jobId,
  jobTitle,
  entries,
  dropOff,
}: {
  jobId: string;
  jobTitle: string;
  entries: readonly RankingEntry[];
  dropOff: DropOff | null;
}) {
  const t = useTranslations("job");
  const locale = useLocale();
  const router = useRouter();
  const [selected, setSelected] = useState<string | undefined>(undefined);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  // The view is the page's own state, seeded from the address and written back to it.
  const searchParams = useSearchParams();
  const [view, setViewState] = useState(() => viewFromParams(searchParams));
  const setView = (next: ListView) => {
    setViewState(next);
    // The history API rather than the router: the list is already here, so the server need not
    // render the page again for every letter typed.
    const query = paramsFromView(next).toString();
    window.history.replaceState(null, "", query === "" ? window.location.pathname : `?${query}`);
  };
  const shown = viewRanking(entries, view, locale);
  const rankedCount = (list: readonly RankingEntry[]) =>
    list.filter((entry) => entry.kind === "ranked").length;
  // The drop-off belongs to the whole ranking in score order; narrowed or resorted, it would mark
  // a break between candidates who are not neighbours.
  const marker = view.sort === "score" && !isNarrowed(view) ? dropOff : null;

  const rows: CandidateRow[] = shown.map((entry): CandidateRow => {
    switch (entry.kind) {
      case "ranked":
        return {
          kind: "ranked",
          id: entry.id,
          rank: entry.rank,
          name: entry.name ?? t("unnamed"),
          reason: entry.reason,
          score: entry.score,
          confidence: entry.confidence,
          needsReview: entry.needsReview,
          href: `/jobs/${jobId}/candidates/${entry.candidateId}`,
          decision: {
            kind: entry.decision,
            ...(entry.decidedBy !== null && { by: entry.decidedBy }),
          },
        };
      case "processing":
        return { kind: "processing", id: entry.id, fileName: entry.label ?? t("unnamed") };
      case "review":
        return { kind: "review", id: entry.id, fileName: entry.label };
      case "failed":
        return {
          kind: "failed",
          id: entry.id,
          fileName: entry.label,
          reason: entry.reason ?? t("failedUnknown"),
        };
    }
  });

  const upload = (files: File[]) => {
    const batch = files.map((file) => ({
      id: crypto.randomUUID(),
      fileName: file.name,
      bytes: file.size,
    }));
    // Batches can overlap: a second drop while the first is still sending. Each batch is added to
    // the list and its handlers change only its own items, found by id.
    const position = new Map(batch.map((item, index) => [item.id, index]));
    const settle = (status: (index: number) => UploadItem["status"]) => {
      setUploads((current) =>
        current.map((item) => {
          const index = position.get(item.id);
          return index === undefined ? item : { ...item, status: status(index) };
        }),
      );
    };
    setUploads((current) => [
      ...current,
      ...batch.map((item): UploadItem => ({ ...item, status: { kind: "uploading", percent: 0 } })),
    ]);

    const form = new FormData();
    for (const file of files) form.append("files", file);
    form.append("jobId", jobId);
    form.append("locale", locale);

    // XMLHttpRequest rather than fetch, because only it reports how much has been sent.
    const request = new XMLHttpRequest();
    request.upload.onprogress = (event) => {
      if (!event.lengthComputable) return;
      const percent = Math.round((event.loaded / event.total) * 100);
      settle(() => ({ kind: "uploading", percent }));
    };
    const failAll = () => {
      settle(() => ({ kind: "failed", reason: t("uploadFailed") }));
    };
    request.onerror = failAll;
    request.onload = () => {
      if (request.status !== 202) {
        failAll();
        return;
      }
      const { files: outcomes } = JSON.parse(request.responseText) as { files: UploadOutcome[] };
      settle((index) => {
        const outcome = outcomes[index];
        if (outcome?.status === "queued" || outcome?.status === "pending") {
          return { kind: "processing" };
        }
        const reason =
          outcome?.status === "rejected" && outcome.reason !== undefined
            ? t(`rejected.${outcome.reason}`)
            : t("uploadFailed");
        return { kind: "failed", reason };
      });
      router.refresh();
    };
    request.open("POST", "/api/uploads");
    request.send(form);
  };

  return (
    <div className={styles.screen}>
      <section aria-label={t("addCvs")} className={styles.uploads}>
        <DropZone job={jobTitle} onFiles={upload} />
        {uploads.length > 0 && <UploadList items={uploads} />}
      </section>
      {entries.length > 0 && (
        <CandidateFilters
          values={view}
          onChange={setView}
          shown={rankedCount(shown)}
          total={rankedCount(entries)}
        />
      )}
      {entries.length === 0 ? (
        <p className={styles.empty}>{t("noCandidates")}</p>
      ) : rows.length === 0 ? (
        <div className={styles.noMatch}>
          <p className={styles.empty}>{t("noMatch")}</p>
          <Button
            variant="secondary"
            onClick={() => {
              setView(DEFAULT_VIEW);
            }}
          >
            {t("clearFilters")}
          </Button>
        </div>
      ) : (
        <CandidateTable
          rows={rows}
          selectedId={selected}
          onSelect={setSelected}
          dropOff={marker}
          sortedBy={view.sort === "recent" ? "none" : view.sort}
        />
      )}
    </div>
  );
}
