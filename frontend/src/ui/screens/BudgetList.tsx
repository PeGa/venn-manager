/** Budget and Goals share this list of budget cards (FRONTEND.md § 5.2, § 5.5). */
import { A } from "@solidjs/router";
import { useQuery } from "@tanstack/solid-query";
import { For, Show, type JSX } from "solid-js";

import { keys } from "@/adapters/queries";
import type { Budget } from "@/domain/model";
import type { BudgetChanges } from "@/ports/api";
import { Button, Card, Skeleton } from "@/ui/components/basics";
import { BudgetCard } from "@/ui/components/BudgetCard";
import { useNotice, useRefresh } from "@/ui/errors";
import { useServices } from "@/ui/services";

export function BudgetList(props: { goals: boolean; trailing?: JSX.Element; empty?: JSX.Element }) {
  const { api, t, narrow } = useServices();
  const budgets = useQuery(() => ({ queryKey: keys.budgets, queryFn: () => api.budgets() }));
  const household = useQuery(() => ({ queryKey: keys.household, queryFn: () => api.household() }));
  const notice = useNotice();
  const refresh = useRefresh();
  const shown = () => budgets.data?.items.filter((budget) => budget.goal === props.goals) ?? [];
  // Keyed by id, so a refetch updates a card instead of remounting it mid-edit.
  const ids = () => shown().map((budget) => budget.id);
  const byId = (id: string) => shown().find((budget) => budget.id === id);

  const update = (budget: Budget) => (changes: BudgetChanges) =>
    api
      .updateBudget(budget.id, changes)
      .then(refresh)
      .catch(notice.report);

  return (
    <Show
      when={budgets.data}
      fallback={
        <Show when={budgets.isError} fallback={<Skeleton lines={4} />}>
          <Card>
            <p class="text-sm text-muted">{t("error_load")}</p>
            <Button class="mt-3" onClick={() => void budgets.refetch()}>
              {t("action_retry")}
            </Button>
          </Card>
        </Show>
      }
    >
      {(data) => (
        <div class="flex flex-col gap-3.5">
          {notice.view()}
          <Show when={shown().length > 0 || props.trailing !== undefined} fallback={props.empty}>
            <div class="grid gap-3.5" classList={{ "grid-cols-2": !narrow(), "grid-cols-1 gap-2.5": narrow() }}>
              <For each={ids()}>
                {(id) => (
                  <Show when={byId(id)}>
                    {(budget) => (
                      <BudgetCard
                        budget={budget()}
                        period={data().period}
                        currencySign={household.data?.currencySign ?? ""}
                        onChange={(changes) => update(budget())(changes)}
                      />
                    )}
                  </Show>
                )}
              </For>
              {props.trailing}
            </div>
          </Show>
        </div>
      )}
    </Show>
  );
}

export function AddConceptLink() {
  const { t, highlight, narrow } = useServices();
  return (
    <A
      href="/settings"
      onClick={() => highlight("settings:budgets")}
      class="grid place-items-center rounded-[18px] border-[1.5px] border-dashed border-[#b9b3a5] text-center text-sm font-semibold text-accent"
      classList={{ "min-h-24": !narrow(), "p-3 text-[13px]": narrow() }}
    >
      {t(narrow() ? "budget_add_short" : "budget_add_long")}
    </A>
  );
}
