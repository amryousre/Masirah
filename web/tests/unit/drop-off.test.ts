import { describe, expect, it } from "vitest";

import { dropOff, MIN_GAP, MIN_RANKED } from "@/lib/domain/drop-off";

// The quality drop-off (T064): where the ranked scores break, found from their distribution rather
// than a fixed rank, so the recruiter knows she can stop reading there.

describe("dropOff", () => {
  it("marks the break after the candidates above a material fall", () => {
    expect(dropOff([91, 88, 86, 85, 83, 64, 62, 60, 57])).toEqual({ above: 5, gap: 19 });
  });

  it("lands wherever the data breaks, not at a fixed rank", () => {
    expect(dropOff([94, 72, 70, 69, 67, 66])).toEqual({ above: 1, gap: 22 });
    const long = [
      ...Array.from({ length: 15 }, (_, i) => 90 - i),
      ...Array.from({ length: 20 }, (_, i) => 55 - i),
    ];
    expect(dropOff(long)).toEqual({ above: 15, gap: 21 });
  });

  it("marks nothing when the scores fall evenly", () => {
    expect(dropOff([90, 85, 80, 75, 70, 65, 60])).toBeNull();
    expect(dropOff([90, 78, 66, 54, 42, 30])).toBeNull();
  });

  it("marks nothing for a fall smaller than the minimum, however flat the rest", () => {
    expect(dropOff([80, 80, 80, 80 - (MIN_GAP - 1), 73, 73])).toBeNull();
  });

  it("marks nothing on a list short enough to read whole", () => {
    expect(dropOff([90, 88, 50, 48].slice(0, MIN_RANKED - 1))).toBeNull();
    expect(dropOff([])).toBeNull();
  });

  it("takes the higher of two equal breaks, where quality first falls", () => {
    expect(dropOff([90, 89, 70, 69, 50, 49])).toEqual({ above: 2, gap: 19 });
  });

  it("reads the scores in rank order whatever order they arrive in", () => {
    expect(dropOff([62, 91, 60, 85, 88, 83, 86])).toEqual({ above: 5, gap: 21 });
  });
});
