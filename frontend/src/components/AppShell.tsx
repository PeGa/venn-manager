/**
 * App shell: the sandwich button, the left drawer and the routed content.
 *
 * FRONTEND.md repeats the same drawer on every screen, so it lives here once.
 * The drawer overlays the content, traps focus while open, and closes on Escape
 * or on navigation (AGENTS.md § Accessibility Baseline).
 */
import type { ComponentChildren } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { Link, useLocation } from "wouter-preact";

import { MonthSwitchDialog } from "./MonthSwitch";
import { useTranslation } from "@/hooks/useTranslation";
import type { UserSummary } from "@/types/api";

interface NavItem {
  path: string;
  labelKey: "nav_home" | "nav_budget" | "nav_concepts" | "nav_history" | "nav_configuration";
}

const NAV_ITEMS: NavItem[] = [
  { path: "/", labelKey: "nav_home" },
  { path: "/budget", labelKey: "nav_budget" },
  { path: "/concepts", labelKey: "nav_concepts" },
  { path: "/history", labelKey: "nav_history" },
  { path: "/configuration", labelKey: "nav_configuration" },
];

export interface AppShellProps {
  user: UserSummary;
  onLogout: () => void;
  children: ComponentChildren;
}

export function AppShell({ user, onLogout, children }: AppShellProps) {
  const t = useTranslation();
  const [open, setOpen] = useState(false);
  const drawer = useRef<HTMLElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);
  const [location] = useLocation();

  // Navigating closes the drawer, so the content is never left behind an overlay.
  useEffect(() => {
    setOpen(false);
  }, [location]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setOpen(false);
        toggle.current?.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    drawer.current?.querySelector<HTMLElement>("a, button")?.focus();
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  return (
    <div class="min-h-screen">
      <header class="sticky top-0 z-30 flex items-center gap-3 border-b border-border bg-canvas px-4 py-3">
        <button
          ref={toggle}
          type="button"
          class="vm-button"
          aria-label={open ? t("menu_close") : t("menu_open")}
          aria-expanded={open}
          aria-controls="app-drawer"
          data-testid="menu-toggle"
          onClick={() => setOpen((value) => !value)}
        >
          <span aria-hidden="true">☰</span>
        </button>
        <h1 class="text-base font-semibold">{t("app_name")}</h1>
        <p class="ml-auto hidden text-sm text-muted sm:block">{user.real_name}</p>
      </header>

      {open ? (
        <>
          <div
            class="fixed inset-0 z-40 bg-black/50"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          <nav
            id="app-drawer"
            ref={drawer}
            aria-label={t("app_name")}
            class="fixed top-0 left-0 z-50 h-full w-64 border-r border-border bg-canvas p-4"
          >
            <ul class="space-y-1">
              {NAV_ITEMS.map((item) => (
                <li key={item.path}>
                  <Link
                    href={item.path}
                    class={`block rounded-md px-3 py-2 text-sm font-medium ${
                      location === item.path
                        ? "bg-selected text-ink"
                        : "text-muted hover:bg-surface"
                    }`}
                  >
                    {t(item.labelKey)}
                  </Link>
                </li>
              ))}
            </ul>
            <button type="button" class="vm-button mt-6 w-full" onClick={onLogout}>
              {t("logout")}
            </button>
          </nav>
        </>
      ) : null}

      <main class="mx-auto w-full max-w-6xl p-4">
        <MonthSwitchDialog />
        {children}
      </main>
    </div>
  );
}
