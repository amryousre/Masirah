// @vitest-environment jsdom
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Confidence, Decision, DocumentStatus } from "@/components/status/status";

import { renderIn } from "./render";

describe("DocumentStatus", () => {
  it.each([
    ["queued", "Queued"],
    ["processing", "Processing"],
    ["parsed", "Parsed"],
    ["needsReview", "Needs review"],
    ["failed", "Couldn't read"],
    ["unsupportedLanguage", "Unsupported language"],
  ] as const)("says %s in words, never by color alone", (status, word) => {
    renderIn("en", <DocumentStatus status={status} />);
    expect(screen.getByText(word)).toBeInTheDocument();
  });

  it("speaks Arabic in Arabic", () => {
    renderIn("ar", <DocumentStatus status="needsReview" />);
    expect(screen.getByText("يحتاج مراجعة")).toBeInTheDocument();
  });
});

describe("Confidence", () => {
  it.each([
    ["high", 3],
    ["medium", 2],
    ["low", 1],
  ] as const)("shows %s as a word and %i of three steps", (level, steps) => {
    const { container } = renderIn("en", <Confidence level={level} />);
    expect(container.querySelectorAll("[data-step='on']")).toHaveLength(steps);
  });

  it("asks for review when confidence is low", () => {
    renderIn("en", <Confidence level="low" showHint />);
    expect(screen.getByText("Low")).toBeInTheDocument();
    expect(screen.getByText("Review before relying on it")).toBeInTheDocument();
  });
});

describe("Decision", () => {
  it("names who decided and when", () => {
    renderIn("en", <Decision kind="rejected" by="Nourhan Saeed" when="12 Mar 14:32" />);
    expect(screen.getByText("Rejected")).toBeInTheDocument();
    expect(screen.getByText("Nourhan Saeed · 12 Mar 14:32")).toBeInTheDocument();
  });

  it("says plainly when no one has decided", () => {
    renderIn("ar", <Decision kind="undecided" detailed />);
    expect(screen.getByText("جديد")).toBeInTheDocument();
    expect(screen.getByText("لم يُتخذ قرار")).toBeInTheDocument();
  });
});
