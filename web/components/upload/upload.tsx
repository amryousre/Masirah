"use client";

import { useTranslations } from "next-intl";
import { type DragEvent, useId, useState } from "react";

import { MAX_BATCH_FILES } from "@/lib/domain/uploads";

import { Button } from "../button/button";
import { Icon, type IconName } from "../icon/icon";
import styles from "./upload.module.css";

export type UploadStatus =
  | { kind: "queued" }
  | { kind: "uploading"; percent: number }
  | { kind: "processing" }
  | { kind: "parsed"; candidate: string }
  | { kind: "needsReview"; reason: string }
  | { kind: "failed"; reason: string }
  | { kind: "unsupported"; language: string };

export interface UploadItem {
  id: string;
  fileName: string;
  bytes: number;
  status: UploadStatus;
  /** The one action that moves this file on: remove, cancel, review, replace, ignore. */
  action?: { label: string; onAction: () => void };
}

const look: Record<UploadStatus["kind"], { icon: IconName; tone: string }> = {
  queued: { icon: "queued", tone: "muted" },
  uploading: { icon: "spinner", tone: "muted" },
  processing: { icon: "spinner", tone: "muted" },
  parsed: { icon: "checkCircle", tone: "success" },
  needsReview: { icon: "alert", tone: "warning" },
  failed: { icon: "xCircle", tone: "error" },
  unsupported: { icon: "globeOff", tone: "muted" },
};

function fileType(fileName: string): string {
  const dot = fileName.lastIndexOf(".");
  return dot === -1 ? "" : fileName.slice(dot + 1).toUpperCase();
}

/** One row per file, the reason in plain words and one action. Nothing is dropped silently. */
export function UploadList({ items }: { items: readonly UploadItem[] }) {
  const t = useTranslations("upload");

  const describe = (status: UploadStatus): string => {
    switch (status.kind) {
      case "queued":
        return t("queued");
      case "uploading":
        return t("uploading", { percent: status.percent });
      case "processing":
        return t("processing");
      case "parsed":
        return t("parsed", { name: status.candidate });
      case "needsReview":
        return t("needsReview", { reason: status.reason });
      case "failed":
        return t("failed", { reason: status.reason });
      case "unsupported":
        return t("unsupported", { language: status.language });
    }
  };

  const size = (bytes: number): string => {
    const kilobytes = bytes / 1024;
    return kilobytes < 1024
      ? t("sizeKb", { size: String(Math.round(kilobytes)) })
      : t("sizeMb", { size: String(Math.round((kilobytes / 1024) * 10) / 10) });
  };

  const count = (...kinds: UploadStatus["kind"][]) =>
    items.filter((item) => kinds.includes(item.status.kind)).length;

  return (
    <div className={styles.list}>
      <ul className={styles.items}>
        {items.map((item) => (
          <li key={item.id} className={styles.item}>
            <span className={styles.type}>{fileType(item.fileName)}</span>
            <span className={styles.file}>
              <span className={styles.name}>{item.fileName}</span>
              {/* "240 KB" runs left to right, or an Arabic line would set it as "KB 240". */}
              <span className={styles.size} dir="ltr">
                {size(item.bytes)}
              </span>
            </span>
            <span className={styles.status} data-tone={look[item.status.kind].tone}>
              <Icon name={look[item.status.kind].icon} size={13} />
              {describe(item.status)}
            </span>
            {item.action && (
              <Button variant="ghost" className={styles.action} onClick={item.action.onAction}>
                {item.action.label}
              </Button>
            )}
          </li>
        ))}
      </ul>
      <p className={styles.summary}>
        {t("summary", {
          total: items.length,
          parsed: String(count("parsed")),
          review: String(count("needsReview")),
          failed: String(count("failed")),
          unsupported: String(count("unsupported")),
          working: String(count("queued", "uploading", "processing")),
        })}
      </p>
    </div>
  );
}

interface DropZoneProps {
  /** The job the files are added to, named while they are dragged over. */
  job: string;
  onFiles: (files: File[]) => void;
  max?: number;
  /** At the processing limit the zone takes nothing, and says when it renews. */
  /** Processing is paused for the month. The limit is the CV count reached, or null when
   *  something else paused it, the spend ceiling, so no count is named that was not reached. */
  limitReached?: { limit: number | null; renewsOn: string } | undefined;
}

export function DropZone({ job, onFiles, max = MAX_BATCH_FILES, limitReached }: DropZoneProps) {
  const t = useTranslations("upload");
  const promptId = useId();
  const hintId = useId();
  const [dragging, setDragging] = useState<number | null>(null);
  const [leftOut, setLeftOut] = useState(0);
  const disabled = limitReached !== undefined;

  // At most `max` files per drop or choice (FR-001). The rest are not taken, and the zone says
  // how many, rather than dropping them silently.
  const accept = (files: File[]) => {
    setLeftOut(Math.max(files.length - max, 0));
    onFiles(files.slice(0, max));
  };

  const onDrag = (event: DragEvent<HTMLDivElement>) => {
    if (disabled) return;
    event.preventDefault();
    setDragging(event.dataTransfer.items.length);
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(null);
    if (!disabled) accept([...event.dataTransfer.files]);
  };

  return (
    <div
      data-testid="drop-zone"
      className={styles.zone}
      data-state={disabled ? "disabled" : dragging !== null ? "over" : "idle"}
      onDragEnter={onDrag}
      onDragOver={onDrag}
      onDragLeave={() => {
        setDragging(null);
      }}
      onDrop={onDrop}
    >
      <Icon name={disabled ? "pauseCircle" : "upload"} size={20} strokeWidth={1.75} />
      {/* The input covers the whole zone, and whatever the zone says is its name, in every state:
          the limit, the drop about to happen, or the invitation. */}
      <p id={promptId} className={styles.prompt}>
        {disabled
          ? limitReached.limit === null
            ? t("paused")
            : t("limitReached", { limit: limitReached.limit })
          : dragging !== null
            ? t("dropNow", { count: dragging })
            : t("drop", { max })}
      </p>
      <p id={hintId} className={styles.hint}>
        {disabled
          ? t("limitDetail", { date: limitReached.renewsOn })
          : dragging !== null
            ? t("destination", { job })
            : t("formats")}
      </p>
      <input
        aria-labelledby={promptId}
        aria-describedby={hintId}
        type="file"
        multiple
        accept=".pdf,.docx,.doc,.jpg,.jpeg,.png"
        disabled={disabled}
        className={styles.input}
        onChange={(event) => {
          accept([...(event.target.files ?? [])]);
          event.target.value = "";
        }}
      />
      <p role="status" className={styles.leftOut}>
        {leftOut > 0 && t("tooMany", { extra: leftOut, max })}
      </p>
    </div>
  );
}
