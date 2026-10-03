/** The add bar (FRONTEND.md § 5.3): payee, literal signed amount, category, Add. */
import { A } from "@solidjs/router";
import { createSignal, Show } from "solid-js";

import type { Budget } from "@/domain/model";
import { parseAmount } from "@/domain/money";
import type { NewTransaction } from "@/ports/api";
import { Button } from "@/ui/components/basics";
import { useServices } from "@/ui/services";

export const UNTITLED = "Untitled";

/** The budget after *current* in creation order, wrapping around. */
export function nextBudget(budgets: Budget[], current: string | null): string | null {
  if (budgets.length === 0) return null;
  const index = budgets.findIndex((budget) => budget.id === current);
  return budgets[(index + 1) % budgets.length]?.id ?? null;
}

export function AddBar(props: { budgets: Budget[]; add: (transaction: NewTransaction) => Promise<boolean> }) {
  const { t, narrow } = useServices();
  const [payee, setPayee] = createSignal("");
  const [amount, setAmount] = createSignal("");
  const [chosen, setChosen] = createSignal<string | null>(null);
  const budgetId = () => {
    const id = chosen();
    return props.budgets.some((budget) => budget.id === id) ? id : (props.budgets[0]?.id ?? null);
  };
  const budgetName = () => props.budgets.find((budget) => budget.id === budgetId())?.name ?? "";
  const cents = () => parseAmount(amount());
  const ready = () => budgetId() !== null && (cents() ?? 0) !== 0;

  const submit = async () => {
    const id = budgetId();
    const value = cents();
    if (id === null || value === null || value === 0) return;
    const saved = await props.add({ payee: payee().trim() || UNTITLED, budgetId: id, amount: value });
    if (saved) {
      setPayee("");
      setAmount("");
    }
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
        class="flex items-center"
        classList={{
          "gap-2.5 rounded-2xl border border-card-border bg-card px-3.5 py-3": !narrow(),
          "gap-1.5": narrow(),
        }}
      >
        <input
          aria-label={t("field_payee")}
          placeholder={t("field_payee")}
          value={payee()}
          maxLength={120}
          onInput={(event) => setPayee(event.currentTarget.value)}
          onKeyDown={onEnter}
          class={`${input} flex-1`}
        />
        <input
          aria-label={t("field_amount")}
          placeholder={narrow() ? "0.00" : t("field_amount")}
          inputmode="decimal"
          value={amount()}
          onInput={(event) => setAmount(event.currentTarget.value)}
          onKeyDown={onEnter}
          class={`${input} font-mono`}
          classList={{ "w-[100px]": !narrow(), "w-[72px]": narrow() }}
        />
        <button
          type="button"
          aria-label={t("category_button", { name: budgetName() })}
          onClick={() => setChosen(nextBudget(props.budgets, budgetId()))}
          class="truncate rounded-control border border-input-border bg-card py-2.5 text-[13px]"
          classList={{ "max-w-[160px] px-3": !narrow(), "max-w-[84px] px-2 text-xs": narrow() }}
        >
          {budgetName()}
        </button>
        <Button kind="primary" disabled={!ready()} onClick={() => void submit()} aria-label={t("action_add")}>
          {narrow() ? "+" : t("action_add")}
        </Button>
      </div>
    </Show>
  );
}
