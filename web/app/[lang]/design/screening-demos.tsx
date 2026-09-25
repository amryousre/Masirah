"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/button/button";
import { type CandidateRow, CandidateTable } from "@/components/candidates/candidate-table";
import { Justification, QuoteList } from "@/components/evidence/evidence";
import { RejectDialog } from "@/components/reject-dialog/reject-dialog";
import { DropZone, UploadList } from "@/components/upload/upload";
import { UsageMeter } from "@/components/usage-meter/usage-meter";

import styles from "./design.module.css";

// The screening specimens on the design page. Each keeps its own state; none of them saves.

export function EvidenceDemo() {
  const t = useTranslations("gallery.evidence");
  const [selected, setSelected] = useState(1);
  return (
    <div className={styles.evidence}>
      <h3 className={styles.demoHeading}>{t("heading")}</h3>
      <Justification
        parts={[
          { claim: 1, text: t("claim1") },
          t("between1"),
          { claim: 2, text: t("claim2") },
          t("between2"),
          { claim: 3, text: t("claim3"), absence: true },
          t("end"),
        ]}
        selected={selected}
        onSelect={setSelected}
      />
      <QuoteList
        quotes={[
          {
            claim: 1,
            kind: "quote",
            page: 1,
            section: t("section"),
            text: t("quote1"),
            lang: "en",
          },
          {
            claim: 2,
            kind: "quote",
            page: 1,
            section: t("section"),
            text: t("quote2"),
            lang: "en",
          },
          { claim: 3, kind: "absence", searched: [t("term1"), "Jest", "Cypress", "Testing"] },
          { claim: 4, kind: "missing" },
        ]}
        selected={selected}
        onSelect={setSelected}
      />
    </div>
  );
}

export function CandidatesDemo() {
  const t = useTranslations("gallery.candidates");
  const [selected, setSelected] = useState("c3");
  const rows: CandidateRow[] = [
    {
      kind: "ranked",
      id: "c1",
      rank: 1,
      name: t("name1"),
      reason: t("reason1"),
      score: 86,
      confidence: "high",
      decision: { kind: "shortlisted", by: t("tarek") },
    },
    {
      kind: "ranked",
      id: "c2",
      rank: 2,
      name: t("name2"),
      reason: t("reason2"),
      score: 81,
      confidence: "high",
      decision: { kind: "undecided" },
    },
    {
      kind: "ranked",
      id: "c3",
      rank: 3,
      name: t("name3"),
      reason: t("reason3"),
      score: 78,
      confidence: "medium",
      decision: { kind: "undecided" },
    },
    {
      kind: "ranked",
      id: "c4",
      rank: 4,
      name: t("name4"),
      reason: t("reason4"),
      score: 71,
      confidence: "low",
      decision: { kind: "undecided" },
      needsReview: true,
    },
    {
      kind: "ranked",
      id: "c5",
      rank: 5,
      name: t("name5"),
      reason: t("reason5"),
      score: 41,
      confidence: "high",
      decision: { kind: "rejected", by: t("nourhan") },
    },
    { kind: "processing", id: "f1", fileName: "Ahmed_Samir_CV.docx" },
    { kind: "failed", id: "f2", fileName: "scan_0231.jpg", reason: t("blurred") },
  ];
  return <CandidateTable rows={rows} selectedId={selected} onSelect={setSelected} />;
}

export function UploadDemo() {
  const t = useTranslations("gallery.upload");
  const upload = useTranslations("upload");
  const [dropped, setDropped] = useState<string[]>([]);
  const noop = () => undefined;
  return (
    <div className={styles.stack}>
      <DropZone
        job={t("job")}
        onFiles={(files) => {
          setDropped(files.map((file) => file.name));
        }}
      />
      {dropped.length > 0 && (
        <UploadList
          items={dropped.map((name, index) => ({
            id: `new-${String(index)}`,
            fileName: name,
            bytes: 0,
            status: { kind: "queued" },
          }))}
        />
      )}
      <UploadList
        items={[
          {
            id: "1",
            fileName: "CV_Sara_Nabil.pdf",
            bytes: 240 * 1024,
            status: { kind: "queued" },
            action: { label: upload("remove"), onAction: noop },
          },
          {
            id: "2",
            fileName: "Ahmed_Samir_CV.docx",
            bytes: 1.2 * 1024 * 1024,
            status: { kind: "uploading", percent: 64 },
            action: { label: upload("cancel"), onAction: noop },
          },
          {
            id: "3",
            fileName: "Yasmin_Farouk.pdf",
            bytes: 310 * 1024,
            status: { kind: "parsed", candidate: t("yasmin") },
            action: { label: upload("openProfile"), onAction: noop },
          },
          {
            id: "4",
            fileName: "IMG_2231.jpg",
            bytes: 3.4 * 1024 * 1024,
            status: { kind: "needsReview", reason: t("tilted") },
            action: { label: upload("review"), onAction: noop },
          },
          {
            id: "5",
            fileName: "CV_final_v3.pdf",
            bytes: 1.1 * 1024 * 1024,
            status: { kind: "failed", reason: t("locked") },
            action: { label: upload("replace"), onAction: noop },
          },
          {
            id: "6",
            fileName: "Lebenslauf_Weber.pdf",
            bytes: 520 * 1024,
            status: { kind: "unsupported", language: t("german") },
            action: { label: upload("ignore"), onAction: noop },
          },
        ]}
      />
      <DropZone
        job={t("job")}
        onFiles={noop}
        limitReached={{ limit: 300, renewsOn: t("renews") }}
      />
    </div>
  );
}

export function UsageDemo() {
  const t = useTranslations("gallery.usage");
  const noop = () => undefined;
  return (
    <div className={styles.meters}>
      <UsageMeter used={126} limit={300} renewsOn={t("renews")} />
      <UsageMeter used={246} limit={300} renewsOn={t("renews")} />
      <UsageMeter
        used={300}
        limit={300}
        renewsOn={t("renews")}
        waiting={14}
        onUpgrade={noop}
        onViewUsage={noop}
      />
      <UsageMeter loading />
    </div>
  );
}

/** The usage meter as it sits in the app frame's sidebar. */
export function FrameUsage() {
  const t = useTranslations("gallery.usage");
  return <UsageMeter used={126} limit={300} renewsOn={t("renews")} />;
}

export function RejectDemo() {
  const t = useTranslations("gallery.reject");
  const [open, setOpen] = useState(false);
  const close = () => {
    setOpen(false);
  };
  return (
    <>
      <Button
        variant="destructive"
        onClick={() => {
          setOpen(true);
        }}
      >
        {t("open")}
      </Button>
      <RejectDialog
        open={open}
        candidate={t("candidate")}
        actor={t("actor")}
        when={t("when")}
        reasons={[
          { value: "skills", label: t("skills") },
          { value: "experience", label: t("experience") },
          { value: "location", label: t("location") },
        ]}
        onCancel={close}
        onConfirm={close}
      />
    </>
  );
}
