/** Localization hook. Provides translation function using locale files. */
import { useSettings } from "./useSettings.ts";
import { translations, type LocaleKey } from "../utils/l10n.ts";

export const useLocale = () => {
  const { settings } = useSettings();
  const lang = (settings?.language ?? "en") as LocaleKey;

  const t = (key: string): string => {
    const locale = translations[lang] ?? translations.en;
    return locale[key] ?? translations.en[key] ?? key;
  };

  return { t, lang };
};
