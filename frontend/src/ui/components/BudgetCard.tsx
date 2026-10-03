/**
 * One budget, on Budget or Goals (FRONTEND.md § 4.2). The stepper and the
 * typed amount update the card at once and save 400 ms after the last change.
 */
import { createSignal, onCleanup, Show } from "solid-js";

import { budgetNote, figures, stepAmount } from "@/domain/budgets";
import { periodLabel, scheduleSummary } from "@/domain/dates";
import type { Budget, Cents, Period, Schedule } from "@/domain/model";
import { parseAmount } from "@/domain/money";
import type { BudgetChanges } from "@/ports/api";
import { Bar } from "@/ui/components/basics";
import { Highlight } from "@/ui/components/Highlight";
import { ScheduleDialog } from "@/ui/components/ScheduleDialog";
import { useServices } from "@/ui/services";

export const SAVE_DELAY_MS = 400;

function plain(cents: Cents): string {
  return String(cents / 100);
}

export function BudgetCard(props: {
  budget: Budget;
  period: Period;
  currencySign: string;
  onChange: (changes: BudgetChanges) => Promise<unknown>;
}) {
  const { t, language, narrow } = useServices();
  const [draft, setDraft] = createSignal<Cents | null>(null);
  const [typing, setTyping] = createSignal<string | null>(null);
  const [scheduling, setScheduling] = createSignal(false);
  let timer: ReturnType<typeof setTimeout> | undefined;

  const amount = () => draft() ?? props.budget.amount;
  const live = () => figures(amount(), props.budget.actual);
  const note = () => budgetNote(language(), props.currencySign, amount(), props.budget.actual, props.budget.goal);

  const flush = () => {
    clearTimeout(timer);
    timer = undefined;
    const value = draft();
    if (value === null) return;
    // Untracked on purpose: only clear the draft if nothing newer was typed.
    // eslint-disable-next-line solid/reactivity
    void props.onChange({ amount: value }).finally(() => {
      if (draft() === value) setDraft(null);
    });
  };
  onCleanup(() => {
    if (timer !== undefined) flush();
  });

  const change = (value: Cents) => {
    setDraft(value);
    clearTimeout(timer);
    timer = setTimeout(flush, SAVE_DELAY_MS);
  };

  const saveSchedule = (schedule: Schedule | null) => {
    setScheduling(false);
    void props.onChange({ schedule });
  };

  const stepper = "grid h-7 w-7 place-items-center rounded-lg border border-input-border bg-input-bg text-base";
  return (
    <Highlight key={`budget:${props.budget.id}`} class="rounded-[18px]">
      <section
        aria-label={props.budget.name}
        class="rounded-[18px] border-[1.5px] border-card-border bg-card"
        classList={{ "px-[18px] py-4": !narrow(), "px-3.5 py-3": narrow() }}
      >
        <div class="flex items-center justify-between gap-3">
          <div class="min-w-0">
            <h3 class="truncate font-bold">{props.budget.name}</h3>
            <p class="mt-0.5 font-mono text-[10px] font-medium text-faint">
              {periodLabel(language(), props.period.start, props.period.end)}
            </p>
          </div>
          <div class="flex flex-none items-center gap-1.5">
            <button type="button" class={stepper} aria-label={t("stepper_decrease")} onClick={() => change(stepAmount(amount(), -1))}>
              −
            </button>
            <span class="font-mono text-[13px] font-medium text-muted">{props.currencySign}</span>
            <input
              aria-label={t("budget_amount_label", { name: props.budget.name })}
              inputmode="decimal"
              value={typing() ?? plain(amount())}
              onInput={(event) => {
                const value = event.currentTarget.value;
                setTyping(value);
                const parsed = parseAmount(value);
                if (parsed !== null) change(parsed);
              }}
              onBlur={() => setTyping(null)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  flush();
                  setTyping(null);
                }
              }}
              class="rounded-lg border border-input-border bg-card px-1 py-[5px] text-center font-mono text-sm font-medium"
              classList={{ "w-16": !narrow(), "w-[58px] text-[13px]": narrow() }}
            />
            <button type="button" class={stepper} aria-label={t("stepper_increase")} onClick={() => change(stepAmount(amount(), 1))}>
              +
            </button>
          </div>
        </div>
        <div class="mt-3">
          <Bar pct={live().progressPct} alert={note().alert} label={props.budget.name} />
        </div>
        <p class="mt-1.5 text-xs" classList={{ "text-coral-text": note().alert, "text-muted": !note().alert }}>
          {note().text}
        </p>
        <div class="mt-2.5 flex items-center justify-between gap-2 border-t border-hairline pt-2.5">
          <button
            type="button"
            onClick={() => setScheduling(true)}
            class="rounded-chip border border-input-border px-2.5 py-1 text-[11px] font-semibold text-muted"
          >
            {scheduleSummary(language(), props.budget.schedule)}
          </button>
          <label class="flex items-center gap-1.5 text-xs font-semibold text-muted">
            <input
              type="checkbox"
              checked={props.budget.goal}
              onChange={(event) => void props.onChange({ goal: event.currentTarget.checked })}
              class="h-4 w-4 accent-[var(--accent)]"
            />
            {t("goal_label")}
          </label>
        </div>
      </section>
      <Show when={scheduling()}>
        <ScheduleDialog
          open
          name={props.budget.name}
          schedule={props.budget.schedule}
          onSave={saveSchedule}
          onClose={() => setScheduling(false)}
        />
      </Show>
    </Highlight>
  );
}
