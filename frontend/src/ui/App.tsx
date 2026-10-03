/**
 * The root: services, query client, theme and language, then the session gate
 * (FRONTEND.md § 3): sign in, forced password change, or the app.
 */
import { Route, Router } from "@solidjs/router";
import { QueryClientProvider, useQuery } from "@tanstack/solid-query";
import { createEffect, lazy, Match, onCleanup, Switch } from "solid-js";

import { createQueryClient, keys } from "@/adapters/queries";
import type { Session, Theme } from "@/domain/model";
import { resolveLanguage } from "@/l10n";
import { ApiError, type Api } from "@/ports/api";
import { ForceChange } from "@/ui/auth/ForceChange";
import { SignIn } from "@/ui/auth/SignIn";
import { Button } from "@/ui/components/basics";
import { createServices, ServicesProvider, useServices, type ApiHooks } from "@/ui/services";
import { Shell } from "@/ui/Shell";

const Overview = lazy(() => import("@/ui/screens/Overview").then((m) => ({ default: m.Overview })));
const BudgetScreen = lazy(() => import("@/ui/screens/Budget").then((m) => ({ default: m.BudgetScreen })));
const Transactions = lazy(() => import("@/ui/screens/Transactions").then((m) => ({ default: m.Transactions })));
const History = lazy(() => import("@/ui/screens/History").then((m) => ({ default: m.History })));
const Goals = lazy(() => import("@/ui/screens/Goals").then((m) => ({ default: m.Goals })));
const BalanceScreen = lazy(() => import("@/ui/screens/Balance").then((m) => ({ default: m.BalanceScreen })));
const Settings = lazy(() => import("@/ui/screens/Settings").then((m) => ({ default: m.Settings })));
const Profile = lazy(() => import("@/ui/screens/Profile").then((m) => ({ default: m.Profile })));

function codeOf(error: unknown): string | null {
  return error instanceof ApiError ? error.code : null;
}

function applyTheme(theme: Theme) {
  const dark = window.matchMedia("(prefers-color-scheme: dark)");
  const apply = () => {
    const resolved = theme === "system" ? (dark.matches ? "dark" : "light") : theme;
    document.documentElement.dataset["theme"] = resolved;
  };
  apply();
  dark.addEventListener("change", apply);
  onCleanup(() => dark.removeEventListener("change", apply));
}

function Gate() {
  const { api, t, setLanguage } = useServices();
  const session = useQuery(() => ({
    queryKey: keys.session,
    queryFn: () => api.session(),
  }));

  createEffect(() => {
    const data: Session | undefined = session.data;
    setLanguage(resolveLanguage(data?.preferences.language ?? null, navigator.language));
    applyTheme(data?.preferences.theme ?? "system");
  });

  const code = () => codeOf(session.error);
  return (
    <Switch>
      <Match when={session.data?.mustChangePassword === true || code() === "PASSWORD_CHANGE_REQUIRED"}>
        <ForceChange />
      </Match>
      <Match when={code() === "UNAUTHORIZED"}>
        <SignIn />
      </Match>
      <Match when={session.isError}>
        <main class="grid min-h-screen place-items-center p-6">
          <div class="flex flex-col items-center gap-4 text-center">
            <p class="text-sm text-muted">{t("error_load")}</p>
            <Button kind="primary" onClick={() => void session.refetch()}>
              {t("action_retry")}
            </Button>
          </div>
        </main>
      </Match>
      <Match when={session.data}>
        <Router root={Shell}>
          <Route path="/" component={Overview} />
          <Route path="/budget" component={BudgetScreen} />
          <Route path="/transactions" component={Transactions} />
          <Route path="/history" component={History} />
          <Route path="/goals" component={Goals} />
          <Route path="/balance" component={BalanceScreen} />
          <Route path="/settings" component={Settings} />
          <Route path="/profile" component={Profile} />
          <Route path="*" component={Overview} />
        </Router>
      </Match>
    </Switch>
  );
}

/** Mount the app around an API adapter factory. */
export function App(props: { makeApi: (hooks: ApiHooks) => Api }) {
  // eslint-disable-next-line solid/reactivity -- the adapter is built once.
  const services = createServices(props.makeApi, resolveLanguage(null, navigator.language));
  // Any query losing its session re-checks the session; the session query
  // itself is excluded, or a 401 would refetch it forever.
  const client = createQueryClient((error, queryKey) => {
    if (queryKey[0] === keys.session[0]) return;
    if (codeOf(error) === "UNAUTHORIZED" || codeOf(error) === "PASSWORD_CHANGE_REQUIRED") {
      void client.invalidateQueries({ queryKey: keys.session });
    }
  });
  return (
    <ServicesProvider services={services}>
      <QueryClientProvider client={client}>
        <Gate />
      </QueryClientProvider>
    </ServicesProvider>
  );
}
