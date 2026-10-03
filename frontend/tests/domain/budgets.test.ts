import { describe, expect, it } from "vitest";

import { budgetNote, figures, stepAmount } from "@/domain/budgets";

describe("figures (mirror of BACKEND.md § 4.2)", () => {
  it.each([
    [-1000, -500, { actual: -500, projected: -1000, remaining: -500, over: false, overBy: 0, progressPct: 50 }],
    [-1000, -3000, { actual: -3000, projected: -3000, remaining: 0, over: true, overBy: 2000, progressPct: 100 }],
    [-1000, 200, { actual: 200, projected: -1000, remaining: -1200, over: false, overBy: 0, progressPct: 0 }],
    [10000, 11000, { actual: 11000, projected: 11000, remaining: 0, over: true, overBy: 1000, progressPct: 100 }],
    [0, -202600, { actual: -202600, projected: -202600, remaining: 0, over: true, overBy: 202600, progressPct: 0 }],
    [0, 0, { actual: 0, projected: 0, remaining: 0, over: false, overBy: 0, progressPct: 0 }],
  ])("amount %d, actual %d", (amount, actual, expected) => {
    expect(figures(amount, actual)).toEqual(expected);
  });
});

describe("budgetNote", () => {
  const note = (amount: number, actual: number, goal = false) =>
    budgetNote("en", "$", amount, actual, goal);

  it("spending budgets say spent, left and over", () => {
    expect(note(-80000, -60400)).toEqual({ text: "$604 spent · $196 left", alert: false });
    expect(note(-35000, -40000)).toEqual({ text: "$400 spent · $50 over", alert: true });
  });

  it("income budgets say received, to go and above", () => {
    expect(note(224000, 100000)).toEqual({ text: "$1,000 received · $1,240 to go", alert: false });
    expect(note(224000, 230000)).toEqual({ text: "$2,300 received · $60 above", alert: false });
  });

  it("zero budgets ask for an amount", () => {
    expect(note(0, 0)).toEqual({ text: "$0 · Set an amount", alert: false });
    expect(note(0, -202600)).toEqual({ text: "$2,026 spent · Set an amount", alert: true });
    expect(note(0, 5000)).toEqual({ text: "$50 received · Set an amount", alert: true });
  });

  it("goals talk about progress", () => {
    expect(note(-220000, -96000, true)).toEqual({ text: "$960 of $2,200 · $1,240 to go", alert: false });
    expect(note(-220000, -220000, true)).toEqual({ text: "Reached", alert: false });
    expect(note(-220000, -230000, true)).toEqual({ text: "$100 over", alert: true });
  });

  it("speaks Spanish", () => {
    expect(budgetNote("es", "€", -80000, -60400, false).text).toBe(
      "€604 gastado · €196 disponible",
    );
  });
});

describe("stepAmount", () => {
  it("adds and subtracts 50.00 literally", () => {
    expect(stepAmount(-80000, 1)).toBe(-75000);
    expect(stepAmount(-80000, -1)).toBe(-85000);
    expect(stepAmount(0, -1)).toBe(-5000);
  });

  it("stays inside the API range", () => {
    expect(stepAmount(9_999_999_999, 1)).toBe(9_999_999_999);
    expect(stepAmount(-9_999_999_999, -1)).toBe(-9_999_999_999);
  });
});
