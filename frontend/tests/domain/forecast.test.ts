import { describe, expect, it } from "vitest";

import { figures } from "@/domain/budgets";
import { loggedTransactions, plannedLines } from "@/domain/forecast";
import type { Budget, Transaction } from "@/domain/model";

function budget(id: string, amount: number, actual: number): Budget {
  return { id, name: id, amount, schedule: null, goal: false, createdAt: "2026-09-01T10:00:00Z", ...figures(amount, actual) };
}

function transaction(id: string, amount: number, categoryDeleted = false): Transaction {
  return {
    id,
    budgetId: "b",
    category: "B",
    categoryDeleted,
    amount,
    memberId: "m",
    date: "2026-09-02",
    createdAt: "2026-09-02T10:00:00Z",
    updatedAt: "2026-09-02T10:00:00Z",
    archived: false,
  };
}

describe("plannedLines", () => {
  it("keeps budgets with money still to move, in the given order", () => {
    const budgets = [
      budget("income", 10000, 10000),
      budget("gig", 5000, 0),
      budget("gig2", 3000, 0),
      budget("groceries", -1000, -1000),
      budget("clothing", -3000, -3000),
      budget("internet", -500, 0),
      budget("half", -1000, -400),
    ];
    expect(plannedLines(budgets)).toEqual([
      { budgetId: "gig", name: "gig", remaining: 5000 },
      { budgetId: "gig2", name: "gig2", remaining: 3000 },
      { budgetId: "internet", name: "internet", remaining: -500 },
      { budgetId: "half", name: "half", remaining: -600 },
    ]);
  });

  it("is empty when every budget is fulfilled", () => {
    expect(plannedLines([budget("zero", 0, -100)])).toEqual([]);
  });
});

describe("loggedTransactions", () => {
  it("leaves out transactions of deleted budgets, which do not count", () => {
    const rows = [transaction("a", -100), transaction("b", -200, true), transaction("c", 300)];
    expect(loggedTransactions(rows).map((t) => t.id)).toEqual(["a", "c"]);
  });
});
