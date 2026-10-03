import { describe, expect, it } from "vitest";

import {
  clampDateToMonth,
  historyMonths,
  isBeforeMonth,
  monthOf,
  nextMonth,
  previousMonth,
} from "@/utils/months";

describe("clampDateToMonth", () => {
  it("keeps a day that already fits", () => {
    expect(clampDateToMonth("2025-07-15", "2025-09")).toBe("2025-09-15");
  });

  it("clamps the 31st to February in a common year", () => {
    expect(clampDateToMonth("2025-01-31", "2025-02")).toBe("2025-02-28");
  });

  it("clamps the 31st to February in a leap year", () => {
    expect(clampDateToMonth("2024-01-31", "2024-02")).toBe("2024-02-29");
  });

  it("clamps the 31st to a thirty-day month", () => {
    expect(clampDateToMonth("2025-01-31", "2025-04")).toBe("2025-04-30");
  });

  it("never drifts, because the stored day is not rewritten", () => {
    // FRONTEND.md § 2: Jan 31 -> Feb 28 -> Mar 31, not Feb 28 -> Mar 28.
    const stored = "2025-01-31";
    expect(clampDateToMonth(stored, "2025-02")).toBe("2025-02-28");
    expect(clampDateToMonth(stored, "2025-03")).toBe("2025-03-31");
  });

  it("leaves a date already inside the month alone", () => {
    expect(clampDateToMonth("2025-07-04", "2025-07")).toBe("2025-07-04");
  });
});

describe("month arithmetic", () => {
  it("steps back within a year", () => {
    expect(previousMonth("2025-07")).toBe("2025-06");
  });

  it("steps back across a year boundary", () => {
    expect(previousMonth("2025-01")).toBe("2024-12");
  });

  it("steps forward within a year", () => {
    expect(nextMonth("2025-07")).toBe("2025-08");
  });

  it("steps forward across a year boundary", () => {
    expect(nextMonth("2025-12")).toBe("2026-01");
  });

  it("reads the month of an ISO date", () => {
    expect(monthOf("2025-07-15")).toBe("2025-07");
  });

  it("compares months", () => {
    expect(isBeforeMonth("2025-06", "2025-07")).toBe(true);
    expect(isBeforeMonth("2025-07", "2025-07")).toBe(false);
    expect(isBeforeMonth("2025-08", "2025-07")).toBe(false);
    expect(isBeforeMonth("2024-12", "2025-01")).toBe(true);
  });
});

describe("historyMonths", () => {
  it("lists earliest up to the month before the working month", () => {
    expect(historyMonths("2025-05", "2025-07")).toEqual(["2025-05", "2025-06"]);
  });

  it("crosses a year boundary", () => {
    expect(historyMonths("2024-11", "2025-02")).toEqual([
      "2024-11",
      "2024-12",
      "2025-01",
    ]);
  });

  it("returns a single month when the earliest is the previous one", () => {
    expect(historyMonths("2025-06", "2025-07")).toEqual(["2025-06"]);
  });

  it("is empty when the earliest month is the working month", () => {
    // FRONTEND.md § 4: nothing to pick, so the picker stays disabled.
    expect(historyMonths("2025-07", "2025-07")).toEqual([]);
  });

  it("is empty when there are no records at all", () => {
    expect(historyMonths(null, "2025-07")).toEqual([]);
  });

  it("ignores an earliest month after the working month", () => {
    expect(historyMonths("2025-09", "2025-07")).toEqual([]);
  });
});
