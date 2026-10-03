/**
 * App-wide services every component may read: the API port, language,
 * sync state, pointer type and the highlight-on-navigate signal.
 */
import {
  createContext,
  createSignal,
  onCleanup,
  useContext,
  type Accessor,
  type ParentProps,
} from "solid-js";

import {
  plural,
  translate,
  type Language,
  type PluralKey,
  type TranslationKey,
  type TranslationVars,
} from "@/l10n";
import type { Api } from "@/ports/api";

export const HIGHLIGHT_MS = 3500;

export interface Services {
  api: Api;
  language: Accessor<Language>;
  setLanguage: (language: Language) => void;
  t: (key: TranslationKey, vars?: TranslationVars) => string;
  p: (base: PluralKey, count: number, vars?: TranslationVars) => string;
  /** Latest `X-Ledger-Rev` seen, for the sync chip. */
  revision: Accessor<number | null>;
  setRevision: (revision: number) => void;
  /** Whether the latest request failed for network reasons. */
  offline: Accessor<boolean>;
  setOffline: (offline: boolean) => void;
  /** Touch device (FRONTEND.md § 2.2). */
  coarse: Accessor<boolean>;
  /** Narrow viewport (FRONTEND.md § 2.1). */
  narrow: Accessor<boolean>;
  highlighted: Accessor<string | null>;
  highlight: (key: string) => void;
}

const ServicesContext = createContext<Services>();

function media(query: string): Accessor<boolean> {
  const list = window.matchMedia(query);
  const [matches, setMatches] = createSignal(list.matches);
  const update = (event: MediaQueryListEvent) => setMatches(event.matches);
  list.addEventListener("change", update);
  onCleanup(() => { list.removeEventListener("change", update); });
  return matches;
}

/** Hooks an API adapter reports to. */
export interface ApiHooks {
  onRevision: (revision: number) => void;
  onReachable: (reachable: boolean) => void;
}

/** Build the services. Call once, inside the root component. */
export function createServices(
  makeApi: (hooks: ApiHooks) => Api,
  initialLanguage: Language,
): Services {
  const [language, setLanguage] = createSignal(initialLanguage);
  const [revision, setRevision] = createSignal<number | null>(null);
  const [offline, setOffline] = createSignal(false);
  const api = makeApi({ onRevision: setRevision, onReachable: (ok) => setOffline(!ok) });
  const [highlighted, setHighlighted] = createSignal<string | null>(null);
  let timer: ReturnType<typeof setTimeout> | undefined;
  onCleanup(() => { clearTimeout(timer); });
  return {
    api,
    language,
    setLanguage,
    t: (key, vars) => translate(language(), key, vars),
    p: (base, count, vars) => plural(language(), base, count, vars),
    revision,
    setRevision,
    offline,
    setOffline,
    coarse: media("(pointer: coarse)"),
    narrow: media("(max-width: 767px)"),
    highlighted,
    highlight: (key) => {
      clearTimeout(timer);
      setHighlighted(key);
      timer = setTimeout(() => setHighlighted(null), HIGHLIGHT_MS);
    },
  };
}

export function ServicesProvider(props: ParentProps<{ services: Services }>) {
  // The services object is built once and never replaced; its parts are signals.
  // eslint-disable-next-line solid/reactivity
  return <ServicesContext.Provider value={props.services}>{props.children}</ServicesContext.Provider>;
}

/** The services of the running app. */
export function useServices(): Services {
  const services = useContext(ServicesContext);
  if (services === undefined) {
    throw new Error("useServices must run inside ServicesProvider");
  }
  return services;
}
