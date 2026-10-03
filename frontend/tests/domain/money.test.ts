import { describe, expect, it } from "vitest";

import { formatMoney, parseAmount } from "@/domain/money";

describe("formatMoney", () => {
  it("writes negatives with a true minus before the currency sign", () => {
    expect(formatMoney(-162900, "$", { decimals: 0 })).toBe("−$1,629");
  });

  it("shows two decimals and groups thousands", () => {
    expect(formatMoney(224000, "$")).toBe("$2,240.00");
    expect(formatMoney(123456789, "€")).toBe("€1,234,567.89");
  });

  it("adds a plus to positives when signed", () => {
    expect(formatMoney(224000, "$", { signed: true })).toBe("+$2,240.00");
    expect(formatMoney(-8412, "$", { signed: true })).toBe("−$84.12");
  });

  it("never signs zero", () => {
    expect(formatMoney(0, "$", { signed: true })).toBe("$0.00");
  });

  it("rounds whole units half up, away from zero", () => {
    expect(formatMoney(150, "$", { decimals: 0 })).toBe("$2");
    expect(formatMoney(149, "$", { decimals: 0 })).toBe("$1");
    expect(formatMoney(-150, "$", { decimals: 0 })).toBe("−$2");
  });

  it("allows an empty or multi-character currency sign", () => {
    expect(formatMoney(500, "")).toBe("5.00");
    expect(formatMoney(500, "CHF ")).toBe("CHF 5.00");
  });
});

describe("parseAmount", () => {
  it.each([
    ["25", 2500],
    ["-25", -2500],
    ["−25", -2500],
    ["+25", 2500],
    ["84.12", 8412],
    ["84,12", 8412],
    ["0.5", 50],
    [" 1 000.5 ", 100050],
    ["-0", 0],
  ])("parses %j as %d cents", (text, cents) => {
    expect(parseAmount(text)).toBe(cents);
  });

  it.each(["", "  ", "abc", "1,000.50", "1.234", "--5", "5-", "1e3", ".", "+"])(
    "rejects %j",
    (text) => {
      expect(parseAmount(text)).toBeNull();
    },
  );

  it("rejects amounts beyond the API range", () => {
    expect(parseAmount("100000000.00")).toBeNull();
    expect(parseAmount("99999999.99")).toBe(9999999999);
  });
});
