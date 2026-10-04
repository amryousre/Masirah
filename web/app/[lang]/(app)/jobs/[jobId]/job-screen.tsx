"use client";

import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { type CandidateRow, CandidateTable } from "@/components/candidates/candidate-table";
import { DropZone, type UploadItem, UploadList } from "@/components/upload/upload";
import type { RankingEntry } from "@/lib/domain/ranking";

import styles from "./job.module.css";

interface UploadOutcome {
  name: string;
  status: "queued" | "rejected" | "failed";
  reason?: "type" | "size" | "empty";
}

/**
 * The job's working area (T062, T063). Dropping files navigates nowhere: the files appear with
 * their progress, and the ranked list below fills in as the worker reads them (design-brief.md
 * section 5). The list is the server's; refreshing re-reads it after each batch.
 */
export function JobScreen({
  jobId,
  jobTitle,
  entries,
}: {
  jobId: string;
  jobTitle: string;
  entries: readonly RankingEntry[];
}) {
  const t = useTranslations("job");
  const locale = useLocale();
  const router = useRouter();
  const [selected, setSelected] = useState<string | undefined>(undefined);
  const [uploads, setUploads] = useState<UploadItem[]>([]);

  const rows: CandidateRow[] = entries.map((entry): CandidateRow => {
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
    const batch = files.map((file, index) => ({
      id: `${String(Date.now())}-${String(index)}`,
      fileName: file.name,
      bytes: file.size,
    }));
    setUploads(batch.map((item) => ({ ...item, status: { kind: "uploading", percent: 0 } })));

    const form = new FormData();
    for (const file of files) form.append("files", file);
    form.append("jobId", jobId);
    form.append("locale", locale);

    // XMLHttpRequest rather than fetch, because only it reports how much has been sent.
    const request = new XMLHttpRequest();
    request.upload.onprogress = (event) => {
      if (!event.lengthComputable) return;
      const percent = Math.round((event.loaded / event.total) * 100);
      setUploads(batch.map((item) => ({ ...item, status: { kind: "uploading", percent } })));
    };
    const failAll = () => {
      setUploads(
        batch.map((item) => ({ ...item, status: { kind: "failed", reason: t("uploadFailed") } })),
      );
    };
    request.onerror = failAll;
    request.onload = () => {
      if (request.status !== 202) {
        failAll();
        return;
      }
      const { files: outcomes } = JSON.parse(request.responseText) as { files: UploadOutcome[] };
      setUploads(
        batch.map((item, index) => {
          const outcome = outcomes[index];
          if (outcome?.status === "queued") return { ...item, status: { kind: "processing" } };
          const reason =
            outcome?.status === "rejected" && outcome.reason !== undefined
              ? t(`rejected.${outcome.reason}`)
              : t("uploadFailed");
          return { ...item, status: { kind: "failed", reason } };
        }),
      );
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
      {rows.length === 0 ? (
        <p className={styles.empty}>{t("noCandidates")}</p>
      ) : (
        <CandidateTable rows={rows} selectedId={selected} onSelect={setSelected} />
      )}
    </div>
  );
}
