import { describe, expect, it } from "vitest";

import { PIE_COLORS, pieSegments } from "@/domain/pie";

describe("pieSegments", () => {
  it("lays slices end to end as percentages of the total", () => {
    expect(pieSegments([75, 25])).toEqual([
      { start: 0, length: 75, color: PIE_COLORS[0] },
      { start: 75, length: 25, color: PIE_COLORS[1] },
    ]);
  });

  it("uses exact proportions, not rounded percentages", () => {
    const [first, second] = pieSegments([21240, 8800]);
    expect(first!.length + second!.length).toBeCloseTo(100);
    expect(first!.length).toBeCloseTo(70.706, 2);
  });

  it("cycles the palette", () => {
    const segments = pieSegments(Array.from({ length: 9 }, () => 1));
    expect(segments[7]!.color).toBe(PIE_COLORS[0]);
  });

  it("draws nothing for an empty or zero month", () => {
    expect(pieSegments([])).toEqual([]);
    expect(pieSegments([0, 0])).toEqual([]);
  });
});
