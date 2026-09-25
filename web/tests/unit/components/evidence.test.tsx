// @vitest-environment jsdom
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Justification, QuoteList } from "@/components/evidence/evidence";

import { renderIn } from "./render";

const parts = [
  "Four years ",
  { claim: 1, text: "building React apps at Vodafone Egypt" },
  ", the most important skill. ",
  { claim: 2, text: "No automated testing", absence: true },
  ".",
];

describe("Justification", () => {
  it("numbers each claim so it can be traced to its quote", () => {
    renderIn("en", <Justification parts={parts} onSelect={vi.fn()} />);
    expect(
      screen.getByRole("button", { name: /building React apps at Vodafone Egypt\s*1/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /No automated testing\s*2/ })).toBeInTheDocument();
  });

  it("selects a claim when it is chosen", async () => {
    const onSelect = vi.fn();
    renderIn("en", <Justification parts={parts} selected={2} onSelect={onSelect} />);
    expect(screen.getByRole("button", { name: /No automated testing/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await userEvent.click(screen.getByRole("button", { name: /building React apps/ }));
    expect(onSelect).toHaveBeenCalledWith(1);
  });
});

describe("QuoteList", () => {
  it("quotes the CV in its own language, with where it came from", () => {
    renderIn(
      "ar",
      <QuoteList
        quotes={[
          {
            claim: 1,
            kind: "quote",
            page: 1,
            section: "الخبرة",
            text: "Front-end Engineer, Vodafone Egypt (2020 to 2024).",
            lang: "en",
          },
        ]}
        onSelect={vi.fn()}
      />,
    );
    const quote = screen.getByText("Front-end Engineer, Vodafone Egypt (2020 to 2024).");
    expect(quote).toHaveAttribute("lang", "en");
    expect(quote).toHaveAttribute("dir", "auto");
    expect(screen.getByText("ص 1 · الخبرة")).toBeInTheDocument();
  });

  it("marks an absence instead of inventing a quote", () => {
    renderIn(
      "en",
      <QuoteList
        quotes={[{ claim: 2, kind: "absence", searched: ["Jest", "Cypress", "testing"] }]}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText("Absence · no line to quote")).toBeInTheDocument();
    expect(
      screen.getByText("We searched the CV for: Jest, Cypress, testing. None of them appear."),
    ).toBeInTheDocument();
  });

  it("warns when a quote could not be found in the document", () => {
    renderIn("en", <QuoteList quotes={[{ claim: 3, kind: "missing" }]} onSelect={vi.fn()} />);
    expect(
      screen.getByText("This quote wasn't found in the document. Treat the claim as unconfirmed."),
    ).toBeInTheDocument();
  });

  it("selects a quote from its button", async () => {
    const onSelect = vi.fn();
    renderIn(
      "en",
      <QuoteList
        quotes={[
          {
            claim: 1,
            kind: "quote",
            page: 2,
            section: "Experience",
            text: "Led 3 developers.",
            lang: "en",
          },
        ]}
        onSelect={onSelect}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /Show in document/ }));
    expect(onSelect).toHaveBeenCalledWith(1);
  });
});
