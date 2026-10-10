/** The add bar (FRONTEND.md § 5.3): literal signed amount, category, Add. */
import { A } from "@solidjs/router";
import { createSignal, Show } from "solid-js";

import type { Budget } from "@/domain/model";
import { parseAmount } from "@/domain/money";
import type { NewTransaction } from "@/ports/api";
import { Button } from "@/ui/components/basics";
import { CategoryPicker } from "@/ui/components/CategoryPicker";
import { useServices } from "@/ui/services";

export function AddBar(props: { budgets: Budget[]; add: (transaction: NewTransaction) => Promise<boolean> }) {
  const { t, narrow } = useServices();
  const [amount, setAmount] = createSignal("");
  const [chosen, setChosen] = createSignal<string | null>(null);
  const budgetId = () => {
    const id = chosen();
    return props.budgets.some((budget) => budget.id === id) ? id : (props.budgets[0]?.id ?? null);
  };
  const cents = () => parseAmount(amount());
  const ready = () => budgetId() !== null && (cents() ?? 0) !== 0;

  const submit = async () => {
    const id = budgetId();
    const value = cents();
    if (id === null || value === null || value === 0) return;
    if (await props.add({ budgetId: id, amount: value })) setAmount("");
  };
  const onEnter = (event: KeyboardEvent) => {
    if (event.key === "Enter") void submit();
  };
  const input = "min-w-0 rounded-control border border-input-border bg-input-bg px-3 py-2.5 text-sm";

  return (
    <Show
      when={props.budgets.length > 0}
      fallback={
        <A href="/settings" class="rounded-2xl border border-card-border bg-card px-4 py-3 text-sm font-semibold text-accent">
          {t("add_needs_budget")}
        </A>
      }
    >
      <div
        class="relative flex items-center"
        classList={{
          "gap-2.5 rounded-2xl border border-card-border bg-card px-3.5 py-3": !narrow(),
          "gap-1.5": narrow(),
        }}
      >
        <input
          aria-label={t("field_amount")}
          placeholder={narrow() ? "0.00" : t("field_amount")}
          inputmode="decimal"
          value={amount()}
          onInput={(event) => setAmount(event.currentTarget.value)}
          onKeyDown={onEnter}
          class={`${input} flex-1 font-mono`}
        />
        <CategoryPicker budgets={props.budgets} selected={budgetId()} onSelect={setChosen} class="min-w-0 flex-1" />
        <Button kind="primary" disabled={!ready()} onClick={() => void submit()} aria-label={t("action_add")}>
          {narrow() ? "+" : t("action_add")}
        </Button>
      </div>
    </Show>
  );
}
