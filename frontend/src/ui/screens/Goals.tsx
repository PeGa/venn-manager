/** Goals (FRONTEND.md § 5.5): budgets ticked as goals. */
import { A } from "@solidjs/router";

import { Card } from "@/ui/components/basics";
import { BudgetList } from "@/ui/screens/BudgetList";
import { useServices } from "@/ui/services";

export function Goals() {
  const { t } = useServices();
  return (
    <BudgetList
      goals
      empty={
        <Card>
          <p class="text-sm text-muted">{t("goals_empty")}</p>
          <A href="/budget" class="mt-2 inline-block text-sm font-semibold text-accent">
            {t("goals_empty_link")}
          </A>
        </Card>
      }
    />
  );
}
