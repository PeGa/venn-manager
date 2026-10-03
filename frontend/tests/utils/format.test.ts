import { describe, expect, it } from "vitest";

import {
  formatAmount,
  formatMoney,
  formatNullableAmount,
} from "@/utils/format";

describe("formatAmount", () => {
  it("always shows two decimals", () => {
    expect(formatAmount(0)).toBe("0.00");
    expect(formatAmount(45.5)).toBe("45.50");
    expect(formatAmount(1234)).toBe("1234.00");
  });

  it("does not add locale grouping separators", () => {
    // AGENTS.md: no locale-aware number formatting.
    expect(formatAmount(1234567.89)).toBe("1234567.89");
  });

  it("keeps the sign", () => {
    expect(formatAmount(-1750)).toBe("-1750.00");
    expect(formatAmount(-0.5)).toBe("-0.50");
  });

  it("rounds half away from zero if the API ever over-delivers precision", () => {
    expect(formatAmount(0.1 + 0.2)).toBe("0.30");
    expect(formatAmount(45.567)).toBe("45.57");
  });
});

describe("formatNullableAmount", () => {
  it("renders a budget without a reserved amount as empty", () => {
    // FRONTEND.md § 2: the amount may be empty, which is not zero.
    expect(formatNullableAmount(null)).toBe("");
  });

  it("renders zero as zero, not as empty", () => {
    expect(formatNullableAmount(0)).toBe("0.00");
  });
});

describe("formatMoney", () => {
  it("prefixes the currency symbol", () => {
    expect(formatMoney(45.5, "$")).toBe("$45.50");
    expect(formatMoney(-1750, "€")).toBe("€-1750.00");
  });

  it("accepts a multi-codepoint emoji symbol", () => {
    const family = "\u{1F468}\u200D\u{1F469}\u200D\u{1F467}";
    expect(formatMoney(10, family)).toBe(`${family}10.00`);
  });

  it("renders no symbol when currency is empty", () => {
    expect(formatMoney(10, "")).toBe("10.00");
  });
});
