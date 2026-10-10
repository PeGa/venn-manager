/**
 * The rows of the Explain dialog (FRONTEND.md § 5.1): every term of the
 * forecast, so the reader can add it up (BACKEND.md § 4.4).
 */
import type { Budget, Cents, Transaction, Uuid } from "@/domain/model";

/** A budget with money still to move this month. */
export interface PlannedLine {
  budgetId: Uuid;
  name: string;
  remaining: Cents;
}

/** Budgets whose `remaining` is not zero, in the order given; they sum to `planned`. */
export function plannedLines(budgets: Budget[]): PlannedLine[] {
  return budgets
    .filter((budget) => budget.remaining !== 0)
    .map((budget) => ({ budgetId: budget.id, name: budget.name, remaining: budget.remaining }));
}

/** Counted transactions only: a deleted budget's rows count nowhere (BACKEND.md § 4.1). */
export function loggedTransactions(transactions: Transaction[]): Transaction[] {
  return transactions.filter((transaction) => !transaction.categoryDeleted);
}
