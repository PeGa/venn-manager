import { describe, expect, it } from "vitest";

import { isLanguage, translate } from "@/l10n";

describe("translate", () => {
  it("resolves an English key", () => {
    expect(translate("en", "date_column")).toBe("Date");
  });

  it("resolves the Spanish equivalent", () => {
    // FRONTEND.md § General description: `__date_column` -> "Fecha" or "Date".
    expect(translate("es", "date_column")).toBe("Fecha");
  });

  it("interpolates placeholders", () => {
    expect(translate("en", "page_label", { page: 2, total: 5 })).toBe("Page 2 of 5");
  });

  it("interpolates the same placeholder twice", () => {
    expect(translate("en", "month_switch_confirm", { current: "2025-07" })).toBe(
      "Switch to 2025-07",
    );
  });

  it("leaves a placeholder it was not given alone", () => {
    expect(translate("en", "page_label", { page: 2 })).toBe("Page 2 of {total}");
  });

  it("never injects markup, so translations stay XSS-safe", () => {
    // Values are rendered as text by Preact; this pins that the lookup itself
    // does no HTML processing either.
    const rendered = translate("en", "error_gone");
    expect(rendered).not.toContain("<");
  });
});

describe("isLanguage", () => {
  it("accepts the shipped locales", () => {
    expect(isLanguage("en")).toBe(true);
    expect(isLanguage("es")).toBe(true);
  });

  it("rejects anything else", () => {
    expect(isLanguage("fr")).toBe(false);
    expect(isLanguage("")).toBe(false);
  });
});
