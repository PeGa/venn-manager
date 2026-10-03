/**
 * Translation access for components.
 */
import { useCallback, useContext } from "preact/hooks";

import { LocaleContext } from "@/components/LocaleContext";
import { translate, type TranslationVars } from "@/l10n";
import type { TranslationKey } from "@/l10n";

export type Translate = (key: TranslationKey, vars?: TranslationVars) => string;

/** The active locale. */
export function useLocale() {
  return useContext(LocaleContext);
}

/**
 * A bound translator.
 *
 * Memoised on the locale so components that pass `t` down do not re-render their
 * children on every parent render.
 */
export function useTranslation(): Translate {
  const locale = useLocale();
  return useCallback(
    (key: TranslationKey, vars?: TranslationVars) => translate(locale, key, vars),
    [locale],
  );
}
