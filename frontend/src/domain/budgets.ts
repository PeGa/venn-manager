/**
 * Budget figures and card notes (BACKEND.md § 4.2, FRONTEND.md § 4.2).
 *
 * `figures` mirrors the server so a card can update while a stepper write is
 * pending. Server values replace it on the next fetch.
 */
import { formatMoney, CENTS_LIMIT } from "@/domain/money";
import type { Cents } from "@/domain/model";
import { translate, type Language, type TranslationKey } from "@/l10n";

export const STEP: Cents = 5000;

export interface BudgetFigures {
  actual: Cents;
  projected: Cents;
  remaining: Cents;
  over: boolean;
  overBy: Cents;
  progressPct: number;
}

export interface Note {
  text: string;
  /** Coral styling: overspent, or money moved against a zero budget. */
  alert: boolean;
}

/** BACKEND.md § 4.2 for a signed *amount* and signed *actual*. */
export function figures(amount: Cents, actual: Cents): BudgetFigures {
  const projected =
    amount > 0 ? Math.max(amount, actual) : amount < 0 ? Math.min(amount, actual) : actual;
  const over = amount !== 0 ? projected !== amount : actual !== 0;
  const sameSign = amount * actual > 0;
  return {
    actual,
    projected,
    remaining: projected - actual,
    over,
    overBy: over ? Math.abs(actual - amount) : 0,
    progressPct: sameSign ? Math.min(100, (Math.abs(actual) / Math.abs(amount)) * 100) : 0,
  };
}

function noteKey(amount: Cents, actual: Cents, goal: boolean, f: BudgetFigures): TranslationKey {
  if (amount === 0) {
    if (actual === 0) return "note_zero_empty";
    return actual < 0 ? "note_zero_spent" : "note_zero_received";
  }
  if (goal) {
    if (f.over) return "note_goal_over";
    return f.remaining === 0 ? "note_goal_reached" : "note_goal_progress";
  }
  if (amount < 0) return f.over ? "note_spent_over" : "note_spent_left";
  return f.over ? "note_received_above" : "note_received_to_go";
}

/** The line under a budget card's bar, in whole currency units. */
export function budgetNote(
  language: Language,
  currencySign: string,
  amount: Cents,
  actual: Cents,
  goal: boolean,
): Note {
  const f = figures(amount, actual);
  const money = (cents: Cents) => formatMoney(Math.abs(cents), currencySign, { decimals: 0 });
  const key = noteKey(amount, actual, goal, f);
  const text = translate(language, key, {
    actual: money(actual),
    amount: money(amount),
    left: money(f.remaining),
    over: money(f.overBy),
  });
  const alert = f.over && (amount <= 0 || goal);
  return { text, alert };
}

/** The stepper: literal ±50.00 on the signed amount, kept inside the API range. */
export function stepAmount(amount: Cents, direction: 1 | -1): Cents {
  return Math.max(-CENTS_LIMIT, Math.min(CENTS_LIMIT, amount + direction * STEP));
}
