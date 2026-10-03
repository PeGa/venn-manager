/**
 * The active locale, provided once by the app shell.
 *
 * Held in context rather than read from the settings query inside every
 * component, so the login screen — which has no session and therefore no
 * settings — can still render translated text.
 */
import { createContext } from "preact";

import type { Language } from "@/types/api";

export const LocaleContext = createContext<Language>("en");
