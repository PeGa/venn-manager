/** Tests for formatting utilities. */
import { describe, it, expect } from "vitest";
import { formatAmount, formatDate, getCurrentMonth, getToday } from "../src/utils/format.ts";

describe("formatAmount", () => {
  it("formats integer as two decimal places", () => {
    expect(formatAmount(0)).toBe("0.00");
    expect(formatAmount(100)).toBe("100.00");
  });

  it("formats decimal with two places", () => {
    expect(formatAmount(42.5)).toBe("42.50");
    expect(formatAmount(99.99)).toBe("99.99");
  });

  it("rounds to two decimal places", () => {
    expect(formatAmount(10.999)).toBe("11.00");
  });
});

describe("formatDate", () => {
  it("returns date string as-is", () => {
    expect(formatDate("2026-09-15")).toBe("2026-09-15");
  });
});

describe("getCurrentMonth", () => {
  it("returns YYYY-MM format", () => {
    const result = getCurrentMonth();
    expect(result).toMatch(/^\d{4}-\d{2}$/);
  });
});

describe("getToday", () => {
  it("returns YYYY-MM-DD format", () => {
    const result = getToday();
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
