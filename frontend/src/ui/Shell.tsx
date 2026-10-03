/**
 * The frame around every screen (FRONTEND.md § 2): a sidebar on wide screens,
 * a title bar with a dropdown menu on narrow ones.
 */
import { A, useLocation, useNavigate, type RouteSectionProps } from "@solidjs/router";
import { useQuery } from "@tanstack/solid-query";
import { createMemo, createSignal, For, onCleanup, Show, Suspense } from "solid-js";

import { keys } from "@/adapters/queries";
import { localDate, monthTitle } from "@/domain/dates";
import type { TranslationKey } from "@/l10n";
import { Skeleton } from "@/ui/components/basics";
import { useServices } from "@/ui/services";

export const NAV: readonly { path: string; label: TranslationKey }[] = [
  { path: "/", label: "nav_overview" },
  { path: "/budget", label: "nav_budget" },
  { path: "/transactions", label: "nav_transactions" },
  { path: "/history", label: "nav_history" },
  { path: "/goals", label: "nav_goals" },
  { path: "/balance", label: "nav_balance" },
  { path: "/settings", label: "nav_settings" },
];

function useScreenTitle() {
  const location = useLocation();
  const { t } = useServices();
  return () => {
    if (location.pathname === "/profile") return t("nav_profile");
    const item = NAV.find((entry) => entry.path === location.pathname) ?? NAV[0];
    return item === undefined ? "" : t(item.label);
  };
}

function SyncChip(props: { short?: boolean }) {
  const { t, revision, offline } = useServices();
  return (
    <span
      class="font-mono text-[11px] font-medium"
      classList={{ "text-coral-text": offline(), "text-bar-light": !offline() && props.short !== true, "text-accent": !offline() && props.short === true }}
    >
      ●{" "}
      {offline()
        ? t("sync_offline")
        : props.short === true
          ? t("sync_short", { rev: revision() ?? "–" })
          : t("sync_synced", { rev: revision() ?? "–" })}
    </span>
  );
}

function Sidebar(props: { name: string; members: number; signedInAs: string }) {
  const { t, p } = useServices();
  const location = useLocation();
  return (
    <nav aria-label={t("nav_label")} class="flex w-[210px] flex-none flex-col gap-1 bg-primary px-3.5 py-6 text-on-primary">
      <div class="px-2.5 pb-1 text-xl font-bold">{t("app_name")}</div>
      <div class="px-2.5 pb-[18px] text-xs opacity-70">
        {props.name} · {p("members_count", props.members)}
      </div>
      <For each={NAV}>
        {(item) => (
          <A
            href={item.path}
            end
            class="rounded-control px-3 py-2.5 text-sm font-semibold"
            classList={{ "bg-white/15 text-white": location.pathname === item.path }}
          >
            {t(item.label)}
          </A>
        )}
      </For>
      <A href="/profile" class="mt-auto block rounded-xl bg-white/10 p-3 text-xs leading-normal">
        <SyncChip />
        <div>{t("signed_in_as", { name: props.signedInAs })}</div>
      </A>
    </nav>
  );
}

function MenuBar(props: { title: string; signedInAs: string }) {
  const { t } = useServices();
  const location = useLocation();
  const navigate = useNavigate();
  const [open, setOpen] = createSignal(false);
  const onKey = (event: KeyboardEvent) => {
    if (event.key === "Escape") setOpen(false);
  };
  document.addEventListener("keydown", onKey);
  onCleanup(() => document.removeEventListener("keydown", onKey));
  const go = (path: string) => {
    setOpen(false);
    navigate(path);
  };
  return (
    <header class="relative flex-none px-5 pt-4">
      <div class="flex justify-end">
        <SyncChip short />
      </div>
      <div class="flex items-center justify-between pt-1">
        <h1 class="text-[22px] font-bold">{props.title}</h1>
        <button
          type="button"
          aria-label={t("menu")}
          aria-expanded={open()}
          onClick={() => setOpen(!open())}
          class="flex h-11 w-11 flex-col items-center justify-center gap-[5px] rounded-[14px] border border-card-border bg-card"
        >
          <span class="h-0.5 w-[18px] rounded-sm bg-primary dark:bg-ink" />
          <span class="h-0.5 w-[18px] rounded-sm bg-primary dark:bg-ink" />
          <span class="mr-[13px] h-0.5 w-3 self-end rounded-sm bg-primary dark:bg-ink" />
        </button>
      </div>
      <Show when={open()}>
        <div class="fixed inset-0 z-10" aria-hidden="true" onClick={() => setOpen(false)} />
        <div class="absolute inset-x-4 top-[92px] z-20 flex flex-col rounded-[20px] border border-card-border bg-card p-2 shadow-menu">
          <For each={NAV}>
            {(item) => (
              <button
                type="button"
                onClick={() => go(item.path)}
                class="h-12 rounded-xl px-3.5 text-left text-[15px] font-semibold"
                classList={{ "bg-primary text-white": location.pathname === item.path }}
              >
                {t(item.label)}
              </button>
            )}
          </For>
          <button type="button" onClick={() => go("/profile")} class="h-12 rounded-xl border-t border-hairline px-3.5 text-left text-sm text-muted">
            {t("signed_in_as", { name: props.signedInAs })}
          </button>
        </div>
      </Show>
    </header>
  );
}

export function Shell(props: RouteSectionProps) {
  const { api, language, narrow } = useServices();
  const session = useQuery(() => ({ queryKey: keys.session, queryFn: () => api.session() }));
  const household = useQuery(() => ({ queryKey: keys.household, queryFn: () => api.household() }));
  const title = useScreenTitle();
  const activeMembers = () => household.data?.members.filter((m) => m.status === "active").length ?? 0;
  const signedInAs = () => session.data?.member.realName ?? "";
  const month = createMemo(() => {
    const timezone = household.data?.timezone ?? "UTC";
    return monthTitle(language(), localDate(new Date().toISOString(), timezone).slice(0, 7));
  });
  return (
    <div class="flex h-dvh overflow-hidden bg-ground text-ink" classList={{ "flex-col": narrow() }}>
      <Show
        when={narrow()}
        fallback={<Sidebar name={household.data?.name ?? ""} members={activeMembers()} signedInAs={signedInAs()} />}
      >
        <MenuBar title={title()} signedInAs={signedInAs()} />
      </Show>
      <main
        class="flex min-w-0 flex-1 flex-col overflow-y-auto"
        classList={{ "gap-[18px] px-8 py-7": !narrow(), "gap-2.5 px-[18px] pb-4 pt-1.5": narrow() }}
      >
        <Show when={!narrow()}>
          <header>
            <p class="text-[13px] text-muted">{month()}</p>
            <h1 class="text-[26px] font-bold">{title()}</h1>
          </header>
        </Show>
        <Suspense fallback={<Skeleton />}>{props.children}</Suspense>
      </main>
    </div>
  );
}
