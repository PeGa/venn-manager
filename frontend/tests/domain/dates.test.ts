import { describe, expect, it } from "vitest";

import {
  activityTime,
  dayLabel,
  dueStatus,
  localDate,
  monthTitle,
  periodLabel,
  scheduleSummary,
} from "@/domain/dates";

const TODAY = "2026-09-28";

describe("dayLabel", () => {
  it("says today and yesterday, otherwise month and day", () => {
    expect(dayLabel("en", "2026-09-28", TODAY)).toBe("Today");
    expect(dayLabel("en", "2026-09-27", TODAY)).toBe("Yesterday");
    expect(dayLabel("en", "2026-09-26", TODAY)).toBe("Sep 26");
    expect(dayLabel("en", "2026-10-01", TODAY)).toBe("Oct 1");
  });

  it("follows Spanish word order and names", () => {
    expect(dayLabel("es", "2026-09-28", TODAY)).toBe("Hoy");
    expect(dayLabel("es", "2026-09-27", TODAY)).toBe("Ayer");
    expect(dayLabel("es", "2026-09-26", TODAY)).toBe("26 sept");
  });

  it("handles month and year boundaries", () => {
    expect(dayLabel("en", "2026-12-31", "2027-01-01")).toBe("Yesterday");
  });
});

describe("localDate", () => {
  it("reads an instant as a calendar date in the household time zone", () => {
    expect(localDate("2026-09-28T23:30:00Z", "UTC")).toBe("2026-09-28");
    expect(localDate("2026-09-28T23:30:00Z", "Europe/Madrid")).toBe("2026-09-29");
  });
});

describe("activityTime", () => {
  const now = new Date("2026-09-28T10:00:00Z");

  it("says just now for the last five minutes", () => {
    expect(activityTime("en", "2026-09-28T09:56:00Z", now, "UTC", TODAY)).toBe("Just now");
    expect(activityTime("es", "2026-09-28T09:56:00Z", now, "UTC", TODAY)).toBe(
      "Ahora mismo",
    );
  });

  it("falls back to the day label", () => {
    expect(activityTime("en", "2026-09-28T08:00:00Z", now, "UTC", TODAY)).toBe("Today");
    expect(activityTime("en", "2026-09-26T08:00:00Z", now, "UTC", TODAY)).toBe("Sep 26");
  });
});

describe("periodLabel", () => {
  it("uppercases the month and keeps the language's order", () => {
    expect(periodLabel("en", "2026-09-01", "2026-09-30")).toBe("SEP 1–30");
    expect(periodLabel("es", "2026-09-01", "2026-09-30")).toBe("1–30 SEPT");
    expect(periodLabel("en", "2028-02-01", "2028-02-29")).toBe("FEB 1–29");
  });
});

describe("monthTitle", () => {
  it("capitalizes the month and adds the year", () => {
    expect(monthTitle("en", "2026-09")).toBe("September 2026");
    expect(monthTitle("es", "2026-08")).toBe("Agosto 2026");
  });
});

describe("scheduleSummary", () => {
  it("describes every repeat kind", () => {
    expect(scheduleSummary("en", null)).toBe("No due date");
    expect(scheduleSummary("en", { repeat: "once", anchor: "2026-09-15" })).toBe(
      "Once · Sep 15",
    );
    expect(scheduleSummary("en", { repeat: "weekly", anchor: "2026-09-14" })).toBe(
      "Weekly · Mondays",
    );
    expect(scheduleSummary("en", { repeat: "biweekly", anchor: "2026-09-03" })).toBe(
      "Every 2 weeks · from Sep 3",
    );
    expect(scheduleSummary("en", { repeat: "monthly", anchor: "2026-01-01" })).toBe(
      "Monthly · 1st",
    );
    expect(scheduleSummary("en", { repeat: "monthly", anchor: "2026-01-23" })).toBe(
      "Monthly · 23rd",
    );
  });

  it("speaks Spanish", () => {
    expect(scheduleSummary("es", { repeat: "monthly", anchor: "2026-01-01" })).toBe(
      "Mensual · día 1",
    );
    expect(scheduleSummary("es", { repeat: "weekly", anchor: "2026-09-14" })).toBe(
      "Semanal · lunes",
    );
  });
});

describe("dueStatus", () => {
  it("covers overdue, today, tomorrow and later", () => {
    expect(dueStatus("en", "2026-09-30", TODAY, true)).toBe("Overdue");
    expect(dueStatus("en", "2026-09-28", TODAY, false)).toBe("Due today");
    expect(dueStatus("en", "2026-09-29", TODAY, false)).toBe("Due tomorrow");
    expect(dueStatus("en", "2026-10-01", TODAY, false)).toBe("Due in 3 days");
    expect(dueStatus("es", "2026-10-01", TODAY, false)).toBe("Vence en 3 días");
  });
});
