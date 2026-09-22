/** Root application component. Handles routing and auth state. */
import { Route, Switch } from "wouter-preact";
import { LoginPage } from "./LoginPage.tsx";
import { DashboardPage } from "./DashboardPage.tsx";
import { BudgetPage } from "./BudgetPage.tsx";
import { ConceptsPage } from "./ConceptsPage.tsx";
import { HistoryPage } from "./HistoryPage.tsx";
import { ConfigPage } from "./ConfigPage.tsx";
import { ChangePasswordPage } from "./ChangePasswordPage.tsx";
import { useAuth } from "../hooks/useAuth.ts";

export const App = () => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <div class="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  if (!user) {
    return <LoginPage />;
  }

  if (user.must_change_password) {
    return <ChangePasswordPage />;
  }

  return (
    <Switch>
      <Route path="/" component={DashboardPage} />
      <Route path="/budget" component={BudgetPage} />
      <Route path="/concepts" component={ConceptsPage} />
      <Route path="/history" component={HistoryPage} />
      <Route path="/config" component={ConfigPage} />
      <Route path="/config/users" component={ConfigPage} />
    </Switch>
  );
};
