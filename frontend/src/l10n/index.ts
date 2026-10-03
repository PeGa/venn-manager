/**
 * Client-side l10n (FRONTEND.md § General description).
 *
 * Translation keys plus locale files, resolved per user. Only language is
 * localised — numbering, dates and currency are not, which is why the formatters
 * in `utils/format.ts` never call `Intl.NumberFormat`.
 */
import type { Language } from "@/types/api";
import { en, type TranslationKey } from "./en";
import { es } from "./es";

export type { TranslationKey };

export const locales: Record<Language, Record<TranslationKey, string>> = { en, es };

export const languages: Language[] = ["en", "es"];

/** `{placeholder}` values a translation may accept. */
export type TranslationVars = Record<string, string | number>;

export function isLanguage(value: string): value is Language {
  return value === "en" || value === "es";
}

/**
 * Resolve *key* in *locale*, interpolating `{name}` placeholders.
 *
 * An unknown locale falls back to English rather than throwing: a stale value in
 * the database must not blank the whole interface.
 */
export function translate(
  locale: Language,
  key: TranslationKey,
  vars?: TranslationVars,
): string {
  const table = locales[locale] ?? en;
  const template = table[key] ?? en[key];
  if (vars === undefined) {
    return template;
  }
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : match,
  );
}
