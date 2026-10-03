/**
 * Translation lookup (FRONTEND.md § 11). Every visible string goes through
 * `translate` or `plural`. Lookups never produce markup.
 */
import { en } from "@/l10n/en";
import { es } from "@/l10n/es";

export type Language = "en" | "es";
export type TranslationKey = keyof typeof en;
export type TranslationTable = Record<TranslationKey, string>;
export type TranslationVars = Record<string, string | number>;

/** Keys that have plural forms, without their `_<category>` suffix. */
export type PluralKey = {
  [K in TranslationKey]: K extends `${infer Base}_other` ? Base : never;
}[TranslationKey];

export const LANGUAGES: readonly Language[] = ["en", "es"];

const tables: Record<Language, TranslationTable> = { en, es };

/** The string for *key* in *language*, with `{name}` placeholders filled. */
export function translate(
  language: Language,
  key: TranslationKey,
  vars: TranslationVars = {},
): string {
  return tables[language][key].replace(/\{(\w+)\}/g, (placeholder, name: string) =>
    name in vars ? String(vars[name]) : placeholder,
  );
}

/** The plural form of *base* for *count*. `{n}` is the count. */
export function plural(
  language: Language,
  base: PluralKey,
  count: number,
  vars: TranslationVars = {},
  type: Intl.PluralRulesOptions["type"] = "cardinal",
): string {
  const category = new Intl.PluralRules(language, { type }).select(count);
  const candidate = `${base}_${category}`;
  const key = (candidate in en ? candidate : `${base}_other`) as TranslationKey;
  return translate(language, key, { n: count, ...vars });
}

/** The member's saved language, else Spanish browsers get Spanish, else English. */
export function resolveLanguage(saved: Language | null, browser: string): Language {
  if (saved !== null) {
    return saved;
  }
  return browser.toLowerCase().startsWith("es") ? "es" : "en";
}
