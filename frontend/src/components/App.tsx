/**
 * Application root: session gate, locale and theme providers, routing.
 *
 * Four states come out of `GET /auth/session`: loading; signed out (login
 * screen); signed in but restricted, which the backend reports as a 403
 * `PASSWORD_CHANGE_REQUIRED` rather than a payload (password form); and signed
 * in (the shell).
 */
import { Route, Router, Switch } from "wouter-preact";

import { AppShell } from "./AppShell";
import { ForcePasswordScreen, LoginScreen } from "./AuthScreens";
import { ConfigurationScreen } from "./ConfigurationScreen";
import { ConceptsScreen } from "./ConceptsScreen";
import { LocaleContext } from "./LocaleContext";
import { MonthSwitchProvider } from "./MonthSwitch";
import { BudgetScreen, HistoryScreen, HomeScreen } from "./RecordScreens";
import { isPasswordChangeRequired } from "@/api/client";
import { useLogout, useSession } from "@/hooks/useSession";
import { useSettings } from "@/hooks/useSettings";
import { useTranslation } from "@/hooks/useTranslation";
import { useTheme } from "@/hooks/useTheme";
import { isLanguage } from "@/l10n";
import type { Language, UserSummary } from "@/types/api";

/**
 * The locale to use before the settings are reachable.
 *
 * The login screen has no session, so `GET /settings` would only produce a 401.
 * Falling back to the browser language keeps that screen translated.
 */
export function browserLocale(): Language {
  const preferred =
    typeof navigator === "undefined" ? "" : (navigator.language ?? "").toLowerCase();
  return isLanguage(preferred.slice(0, 2)) ? (preferred.slice(0, 2) as Language) : "en";
}

export function App() {
  const session = useSession();

  if (session.isPending) {
    return <BootScreen />;
  }
  const payload = session.data?.data;
  if (payload === undefined) {
    // A restricted session answers this endpoint with 403 rather than a payload,
    // so "no data" is ambiguous. The error code is what tells the two apart:
    // without it a refresh on the forced-change screen would bounce to login and
    // lose the session that is still valid server-side.
    if (isPasswordChangeRequired(session.error)) {
      return (
        <LocaleContext.Provider value={browserLocale()}>
          <ForcePasswordScreen />
        </LocaleContext.Provider>
      );
    }
    return (
      <LocaleContext.Provider value={browserLocale()}>
        <LoginScreen />
      </LocaleContext.Provider>
    );
  }
  if (payload.must_change_password) {
    return (
      <LocaleContext.Provider value={browserLocale()}>
        <ForcePasswordScreen />
      </LocaleContext.Provider>
    );
  }
  return <AuthenticatedApp user={payload.user} />;
}

function AuthenticatedApp({ user }: { user: UserSummary }) {
  const settings = useSettings(true);
  const logout = useLogout();
  const stored = settings.data?.data;
  const locale = stored === undefined ? browserLocale() : stored.language;
  const theme = stored?.theme ?? "system";

  useTheme(theme);

  return (
    <LocaleContext.Provider value={locale}>
      <MonthSwitchProvider enabled>
        <Router>
          <AppShell user={user} onLogout={() => logout.mutate()}>
            <Switch>
              <Route path="/" component={HomeScreen} />
              <Route path="/budget" component={BudgetScreen} />
              <Route path="/concepts" component={ConceptsScreen} />
              <Route path="/history" component={HistoryScreen} />
              <Route path="/configuration">
                <ConfigurationScreen isAdmin={user.is_admin} />
              </Route>
              {/* Unknown paths fall back to Home rather than a dead end. */}
              <Route component={HomeScreen} />
            </Switch>
          </AppShell>
        </Router>
      </MonthSwitchProvider>
    </LocaleContext.Provider>
  );
}

/** Shown while the session is being re-validated on load. */
function BootScreen() {
  const t = useTranslation();
  return (
    <main class="flex min-h-screen items-center justify-center p-4">
      <p class="text-sm text-muted" aria-live="polite">
        {t("loading")}
      </p>
    </main>
  );
}

