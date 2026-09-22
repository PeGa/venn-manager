/** Tests for l10n translation files. */
import { describe, it, expect } from "vitest";
import { translations } from "../src/utils/l10n.ts";

describe("translations", () => {
  it("has en and es locales", () => {
    expect(translations).toHaveProperty("en");
    expect(translations).toHaveProperty("es");
  });

  it("en and es have the same keys", () => {
    const enKeys = Object.keys(translations.en).sort();
    const esKeys = Object.keys(translations.es).sort();
    expect(enKeys).toEqual(esKeys);
  });

  it("all values are non-empty strings", () => {
    for (const [lang, dict] of Object.entries(translations)) {
      for (const [key, value] of Object.entries(dict)) {
        expect(value.length, `${lang}.${key} is empty`).toBeGreaterThan(0);
      }
    }
  });
});
