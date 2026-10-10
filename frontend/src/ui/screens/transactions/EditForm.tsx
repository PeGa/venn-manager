/**
 * Editing one transaction: signed amount and category (FRONTEND.md § 6).
 * Fine pointers get an inline bar, coarse ones a bottom sheet.
 */
import { createSignal, Show } from "solid-js";

import type { Budget, Transaction } from "@/domain/model";
import { parseAmount } from "@/domain/money";
import type { TransactionChanges } from "@/ports/api";
import { Button } from "@/ui/components/basics";
import { CategoryPicker } from "@/ui/components/CategoryPicker";
import { Dialog } from "@/ui/components/Dialog";
import { useServices } from "@/ui/services";

/** Only the fields that differ from *transaction*. `null` while the amount is invalid. */
export function changesOf(
  transaction: Transaction,
  amountText: string,
  budgetId: string,
): TransactionChanges | null {
  const amount = parseAmount(amountText);
  if (amount === null || amount === 0) return null;
  const changes: TransactionChanges = {};
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
  const [amount, setAmount] = createSignal(String(props.transaction.amount / 100));
  // eslint-disable-next-line solid/reactivity
  const [budgetId, setBudgetId] = createSignal(props.transaction.budgetId);
  const changes = () => changesOf(props.transaction, amount(), budgetId());

  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    const pending = changes();
    if (pending === null) return;
    if (Object.keys(pending).length === 0) props.cancel();
    else props.save(pending);
  };

  const field = "min-w-0 rounded-control border border-input-border bg-card px-3 py-2.5 text-sm";
  const picker = (wrapper: string) => (
    <CategoryPicker
      budgets={props.budgets}
      selected={budgetId()}
      onSelect={setBudgetId}
      fallbackName={props.transaction.category}
      class={wrapper}
    />
  );
  const amountField = () => (
    <input
      aria-label={t("field_amount")}
      inputmode="decimal"
      value={amount()}
      onInput={(e) => setAmount(e.currentTarget.value)}
      aria-invalid={changes() === null}
      class={`${field} font-mono`}
      classList={{ "w-[100px]": !coarse(), "border-coral": changes() === null }}
    />
  );

  return (
    <Show
      when={coarse()}
      fallback={
        <form
          aria-label={t("editing")}
          onSubmit={submit}
          class="relative flex items-center gap-2.5 rounded-2xl border-[1.5px] border-accent bg-highlight px-3.5 py-3"
        >
          <b class="text-[13px]">{t("editing")}</b>
          {amountField()}
          {picker("min-w-0 flex-1")}
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
          {amountField()}
          {picker("relative")}
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
