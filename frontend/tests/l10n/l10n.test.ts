import { describe, expect, it } from "vitest";

import { en } from "@/l10n/en";
import { es } from "@/l10n/es";
import { plural, resolveLanguage, translate } from "@/l10n";

describe("translate", () => {
  it("looks a key up in the requested language", () => {
    expect(translate("en", "nav_budget")).toBe("Budget");
    expect(translate("es", "nav_budget")).toBe("Presupuesto");
  });

  it("fills placeholders, including repeated ones", () => {
    expect(translate("en", "period_label", { month: "SEP", start: 1, end: 30 })).toBe(
      "SEP 1–30",
    );
    expect(translate("es", "period_label", { month: "SEPT", start: 1, end: 30 })).toBe(
      "1–30 SEPT",
    );
  });

  it("leaves unknown placeholders visible instead of inventing text", () => {
    expect(translate("en", "period_label", { month: "SEP" })).toBe("SEP {start}–{end}");
  });

  it("never produces markup from values", () => {
    expect(translate("en", "period_label", { month: "<b>", start: 1, end: 2 })).toBe(
      "<b> 1–2",
    );
  });
});

describe("plural", () => {
  it("picks the plural category of the language", () => {
    expect(plural("en", "transactions_count", 1)).toBe("1 transaction");
    expect(plural("en", "transactions_count", 9)).toBe("9 transactions");
    expect(plural("es", "transactions_count", 1)).toBe("1 transacción");
    expect(plural("es", "transactions_count", 0)).toBe("0 transacciones");
  });

  it("supports ordinal rules", () => {
    expect(plural("en", "ordinal", 1, {}, "ordinal")).toBe("1st");
    expect(plural("en", "ordinal", 22, {}, "ordinal")).toBe("22nd");
    expect(plural("en", "ordinal", 13, {}, "ordinal")).toBe("13th");
    expect(plural("es", "ordinal", 3, {}, "ordinal")).toBe("3");
  });
});

describe("resolveLanguage", () => {
  it("prefers the member's saved language", () => {
    expect(resolveLanguage("es", "en-US")).toBe("es");
  });

  it("falls back to Spanish browsers, English for everything else", () => {
    expect(resolveLanguage(null, "es-AR")).toBe("es");
    expect(resolveLanguage(null, "es")).toBe("es");
    expect(resolveLanguage(null, "fr-FR")).toBe("en");
    expect(resolveLanguage(null, "")).toBe("en");
  });
});

describe("locale files", () => {
  it("define the same keys", () => {
    expect(Object.keys(es).sort()).toEqual(Object.keys(en).sort());
  });
});
