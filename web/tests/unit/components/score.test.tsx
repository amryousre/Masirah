// @vitest-environment jsdom
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ScoreBar, ScoreBreakdown } from "@/components/score/score";

import { renderIn } from "./render";

const parts = [
  { key: "skills", earned: 26, weight: 30 },
  { key: "experience", earned: 19, weight: 25 },
  { key: "education", earned: 12, weight: 15 },
  { key: "tenure", earned: 8, weight: 10 },
  { key: "language", earned: 8, weight: 10 },
  { key: "location", earned: 5, weight: 10 },
] as const;

describe("ScoreBar", () => {
  it("shows the number, with the bar only as a second channel", () => {
    const { container } = renderIn("en", <ScoreBar value={78} />);
    expect(screen.getByText("78")).toBeInTheDocument();
    const bar = container.querySelector("[data-bar]");
    expect(bar).toHaveAttribute("aria-hidden", "true");
    expect(bar).toHaveStyle({ "--fill": "78%" });
  });
});

describe("ScoreBreakdown", () => {
  it("shows the total and each part as points earned of its weight", () => {
    renderIn("ar", <ScoreBreakdown total={78} parts={parts} />);
    expect(screen.getByText("78 / 100")).toBeInTheDocument();
    expect(screen.getByText("مطابقة المهارات · الوزن 30")).toBeInTheDocument();
    expect(screen.getByText("26 / 30")).toBeInTheDocument();
    expect(screen.getByText("الموقع · الوزن 10")).toBeInTheDocument();
    expect(screen.getByText("5 / 10")).toBeInTheDocument();
  });

  it("draws every track the same length, filled by the share earned", () => {
    const { container } = renderIn("en", <ScoreBreakdown total={78} parts={parts} />);
    const tracks = [...container.querySelectorAll("[data-track]")];
    expect(tracks).toHaveLength(6);
    expect(tracks[5]).toHaveStyle({ "--fill": "50%" });
  });

  it("says which attributes were left out of the score", () => {
    renderIn("en", <ScoreBreakdown total={78} parts={parts} />);
    expect(
      screen.getByText(
        "Not used in scoring: name, gender, age, photo, nationality and marital status.",
      ),
    ).toBeInTheDocument();
  });

  it("shows under each part what its rating rests on", () => {
    renderIn(
      "en",
      <ScoreBreakdown
        total={78}
        parts={parts.map((part) => ({ ...part, evidence: `${part.key} evidence` }))}
      />,
    );
    expect(screen.getByText("skills evidence")).toBeInTheDocument();
    expect(screen.getByText("location evidence")).toBeInTheDocument();
  });

  it("says so while the score is being calculated", () => {
    renderIn("en", <ScoreBreakdown state="calculating" />);
    expect(screen.getByText("Calculating the score…")).toBeInTheDocument();
  });

  it("explains a missing score instead of showing zero", () => {
    renderIn(
      "en",
      <ScoreBreakdown state="unavailable" reason="The CV couldn't be read, so it wasn't scored." />,
    );
    expect(screen.getByText("No score for this candidate")).toBeInTheDocument();
    expect(screen.getByText("The CV couldn't be read, so it wasn't scored.")).toBeInTheDocument();
    expect(screen.queryByText("0 / 100")).toBeNull();
  });
});
