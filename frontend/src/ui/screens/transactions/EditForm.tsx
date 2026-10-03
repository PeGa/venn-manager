/**
 * Editing one transaction: payee, signed amount, category (FRONTEND.md § 6).
 * Fine pointers get an inline bar, coarse ones a bottom sheet.
 */
import { createSignal, For, Show } from "solid-js";

import type { Budget, Transaction } from "@/domain/model";
import { parseAmount } from "@/domain/money";
import type { TransactionChanges } from "@/ports/api";
import { Button, Chip } from "@/ui/components/basics";
import { Dialog } from "@/ui/components/Dialog";
import { nextBudget, UNTITLED } from "@/ui/screens/transactions/AddBar";
import { useServices } from "@/ui/services";

/** Only the fields that differ from *transaction*. `null` while the amount is invalid. */
export function changesOf(
  transaction: Transaction,
  payee: string,
  amountText: string,
  budgetId: string,
): TransactionChanges | null {
  const amount = parseAmount(amountText);
  if (amount === null || amount === 0) return null;
  const changes: TransactionChanges = {};
  const name = payee.trim() || UNTITLED;
  if (name !== transaction.payee) changes.payee = name;
  if (amount !== transaction.amount) changes.amount = amount;
  if (budgetId !== transaction.budgetId) changes.budgetId = budgetId;
  return changes;
}

export function EditForm(props: {
  transaction: Transaction;
  budgets: Budget[];
  save: (changes: TransactionChanges) => void;
  cancel: () => void;
}) {
  const { t, coarse } = useServices();
  // eslint-disable-next-line solid/reactivity -- the form edits a copy taken when it opens.
  const [payee, setPayee] = createSignal(props.transaction.payee);
  // eslint-disable-next-line solid/reactivity
  const [amount, setAmount] = createSignal(String(props.transaction.amount / 100));
  // eslint-disable-next-line solid/reactivity
  const [budgetId, setBudgetId] = createSignal(props.transaction.budgetId);
  const changes = () => changesOf(props.transaction, payee(), amount(), budgetId());
  const budgetName = () => props.budgets.find((budget) => budget.id === budgetId())?.name ?? props.transaction.category;

  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    const pending = changes();
    if (pending === null) return;
    if (Object.keys(pending).length === 0) props.cancel();
    else props.save(pending);
  };

  const field = "min-w-0 rounded-control border border-input-border bg-card px-3 py-2.5 text-sm";
  const fields = () => (
    <>
      <input aria-label={t("field_payee")} value={payee()} maxLength={120} onInput={(e) => setPayee(e.currentTarget.value)} class={`${field} flex-1`} />
      <input
        aria-label={t("field_amount")}
        inputmode="decimal"
        value={amount()}
        onInput={(e) => setAmount(e.currentTarget.value)}
        aria-invalid={changes() === null}
        class={`${field} font-mono`}
        classList={{ "w-[100px]": !coarse(), "border-coral": changes() === null }}
      />
    </>
  );

  return (
    <Show
      when={coarse()}
      fallback={
        <form
          aria-label={t("editing")}
          onSubmit={submit}
          class="flex items-center gap-2.5 rounded-2xl border-[1.5px] border-accent bg-highlight px-3.5 py-3"
        >
          <b class="text-[13px]">{t("editing")}</b>
          {fields()}
          <button type="button" aria-label={t("category_button", { name: budgetName() })} onClick={() => setBudgetId(nextBudget(props.budgets, budgetId()) ?? budgetId())} class="max-w-[160px] truncate rounded-control border border-input-border bg-card px-3 py-2.5 text-[13px]">
            {budgetName()}
          </button>
          <Button kind="primary" type="submit" disabled={changes() === null}>
            {t("action_save")}
          </Button>
          <Button onClick={() => props.cancel()}>{t("action_cancel")}</Button>
        </form>
      }
    >
      <Dialog open title={t("edit_transaction")} onClose={() => props.cancel()}>
        <form aria-label={t("editing")} onSubmit={submit} class="flex flex-col gap-3">
          <b class="text-[17px]">{t("edit_transaction")}</b>
          {fields()}
          <div class="flex flex-wrap gap-1.5">
            <For each={props.budgets}>
              {(budget) => (
                <Chip active={budget.id === budgetId()} onClick={() => setBudgetId(budget.id)}>
                  {budget.name}
                </Chip>
              )}
            </For>
          </div>
          <div class="mt-2 flex gap-2.5">
            <Button class="flex-1" onClick={() => props.cancel()}>
              {t("action_cancel")}
            </Button>
            <Button class="flex-1" kind="primary" type="submit" disabled={changes() === null}>
              {t("action_save")}
            </Button>
          </div>
        </form>
      </Dialog>
    </Show>
  );
}
