/**
 * Colour theme application (FRONTEND.md § 5.1.5).
 *
 * Resolves `system` against the OS preference once, here, and writes the result
 * to `data-theme` on <html>. Everything downstream is plain CSS, so the rest of
 * the app never needs to know whether the theme was chosen or detected.
 */
import { useEffect } from "preact/hooks";

import type { Theme } from "@/types/api";

const DARK_QUERY = "(prefers-color-scheme: dark)";

/** Apply *theme* to the document, following OS changes while it is `system`. */
export function useTheme(theme: Theme): void {
  useEffect(() => {
    const root = document.documentElement;
    const media = window.matchMedia(DARK_QUERY);

    const apply = (): void => {
      const resolved =
        theme === "system" ? (media.matches ? "dark" : "light") : theme;
      root.dataset.theme = resolved;
    };

    apply();
    if (theme !== "system") {
      return () => {
        delete root.dataset.theme;
      };
    }
    media.addEventListener("change", apply);
    return () => {
      media.removeEventListener("change", apply);
    };
  }, [theme]);
}
