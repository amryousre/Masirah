// @vitest-environment jsdom
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { type CandidateRow, CandidateTable } from "@/components/candidates/candidate-table";

import { renderIn } from "./render";

vi.mock("@/i18n/navigation", () => ({
  Link: ({
    href,
    children,
    ...rest
  }: AnchorHTMLAttributes<HTMLAnchorElement> & { children: ReactNode }) => (
    <a href={String(href)} {...rest}>
      {children}
    </a>
  ),
}));

const rows: CandidateRow[] = [
  {
    kind: "ranked",
    id: "c1",
    rank: 1,
    name: "Yasmin Farouk",
    reason: "Six years of React at Instabug",
    score: 86,
    confidence: "high",
    decision: { kind: "shortlisted", by: "Tarek" },
  },
  {
    kind: "ranked",
    id: "c2",
    rank: 2,
    name: "Mahmoud Ali",
    reason: "Scanned CV; dates partly unreadable",
    score: 71,
    confidence: "low",
    decision: { kind: "undecided" },
    needsReview: true,
  },
  {
    kind: "ranked",
    id: "c3",
    rank: 3,
    name: "Hana Adel",
    reason: "No front-end experience in the CV",
    score: 41,
    confidence: "high",
    decision: { kind: "rejected", by: "Nourhan" },
  },
  { kind: "processing", id: "f1", fileName: "Ahmed_Samir_CV.docx" },
  { kind: "failed", id: "f2", fileName: "scan_0231.jpg", reason: "the image is blurred" },
];

describe("CandidateTable", () => {
  it("lists ranked candidates with their reason before their score", () => {
    renderIn("en", <CandidateTable rows={rows} onSelect={vi.fn()} />);
    const headers = screen.getAllByRole("columnheader").map((cell) => cell.textContent);
    expect(headers).toEqual(["#", "Candidate", "Why ranked here", "Score", "Confidence", "Status"]);
    const first = screen.getByRole("row", { name: /Yasmin Farouk/ });
    expect(within(first).getByText("Six years of React at Instabug")).toBeInTheDocument();
    expect(within(first).getByText("86")).toBeInTheDocument();
  });

  it("selects a candidate from their name, and marks the selection", async () => {
    const onSelect = vi.fn();
    renderIn("en", <CandidateTable rows={rows} selectedId="c1" onSelect={onSelect} />);
    expect(screen.getByRole("button", { name: "Yasmin Farouk" })).toHaveAttribute(
      "aria-current",
      "true",
    );
    await userEvent.click(screen.getByRole("button", { name: "Mahmoud Ali" }));
    expect(onSelect).toHaveBeenCalledWith("c2");
  });

  it("asks for review when confidence is low", () => {
    renderIn("en", <CandidateTable rows={rows} onSelect={vi.fn()} />);
    const row = screen.getByRole("row", { name: /Mahmoud Ali/ });
    expect(within(row).getByText("Low confidence · review")).toBeInTheDocument();
  });

  it("keeps a rejected candidate visible, with who decided", () => {
    renderIn("en", <CandidateTable rows={rows} onSelect={vi.fn()} />);
    const row = screen.getByRole("row", { name: /Hana Adel/ });
    expect(row).toHaveAttribute("data-rejected");
    expect(within(row).getByText("Rejected · Nourhan")).toBeInTheDocument();
  });

  it("never hides a document that is not ranked yet", () => {
    renderIn("ar", <CandidateTable rows={rows} onSelect={vi.fn()} />);
    expect(screen.getByRole("rowgroup", { name: "لم تُرتَّب بعد" })).toBeInTheDocument();
    expect(screen.getByText("Ahmed_Samir_CV.docx")).toBeInTheDocument();
    expect(screen.getByText("قيد المعالجة")).toBeInTheDocument();
    expect(screen.getByText("تعذّرت القراءة: the image is blurred")).toBeInTheDocument();
  });

  it("marks where scores fall off, between the last strong candidate and the next", () => {
    renderIn(
      "en",
      <CandidateTable rows={rows} dropOff={{ above: 2, gap: 30 }} onSelect={vi.fn()} />,
    );
    const texts = screen.getAllByRole("row").map((row) => row.textContent);
    const marker = texts.findIndex((text) => text.includes("Scores drop 30 points below here"));
    expect(texts[marker - 1]).toContain("Mahmoud Ali");
    expect(texts[marker + 1]).toContain("Hana Adel");
  });

  it("links a name to the candidate's own page when it has one", () => {
    const linked = rows.map((row) =>
      row.kind === "ranked" ? { ...row, href: `/jobs/j1/candidates/${row.id}` } : row,
    );
    renderIn("en", <CandidateTable rows={linked} onSelect={vi.fn()} />);
    expect(screen.getByRole("link", { name: "Yasmin Farouk" })).toHaveAttribute(
      "href",
      "/jobs/j1/candidates/c1",
    );
  });

  it("keeps a candidate whose data was deleted in the list, saying so and nothing more", () => {
    renderIn(
      "en",
      <CandidateTable rows={[...rows, { kind: "removed", id: "gone" }]} onSelect={vi.fn()} />,
    );
    const row = screen.getByRole("row", { name: "Personal data deleted" });
    expect(row).toHaveTextContent(/^Personal data deleted$/);
  });

  it("marks nothing when the scores have no break", () => {
    renderIn("en", <CandidateTable rows={rows} onSelect={vi.fn()} />);
    expect(screen.queryByText(/Scores drop/)).not.toBeInTheDocument();
  });

  it("says the fall in Arabic, the noun agreeing with the number", () => {
    renderIn(
      "ar",
      <CandidateTable rows={rows} dropOff={{ above: 2, gap: 12 }} onSelect={vi.fn()} />,
    );
    expect(screen.getByText("تنخفض الدرجات 12 نقطة بعد هذا الحد")).toBeInTheDocument();
  });
});
