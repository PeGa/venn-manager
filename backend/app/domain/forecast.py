"""Left to spend and the month-end forecast (BACKEND.md § 4.3, § 4.4)."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.budgets import figures


@dataclass(frozen=True)
class BudgetLine:
    """One non-deleted budget: its signed amount and this period's signed actual."""

    amount: int
    actual: int
    goal: bool = False


@dataclass(frozen=True)
class BudgetTotals:
    """The "Left to spend" hero (BACKEND.md § 4.3)."""

    limit: int
    spent: int
    left_to_spend: int
    spent_pct: float


@dataclass(frozen=True)
class Forecast:
    """The month-end forecast (BACKEND.md § 4.4)."""

    start_cash: int
    planned: int
    transactions_net: int
    transaction_count: int
    total: int


def budget_totals(lines: list[BudgetLine]) -> BudgetTotals:
    """Spending budgets only; goals are money set aside on purpose."""
    spending = [line for line in lines if not line.goal]
    limit = sum(-line.amount for line in spending if line.amount < 0)
    spent = sum(max(0, -line.actual) for line in spending if line.amount <= 0)
    pct = min(100.0, spent / limit * 100) if limit else 0.0
    return BudgetTotals(limit, spent, limit - spent, pct)


def forecast(
    opening_balance: int, earlier_net: int, lines: list[BudgetLine], count: int
) -> Forecast:
    """`total = startCash + planned + transactionsNet` (BACKEND.md § 4.4).

    *earlier_net* is the signed sum of counted transactions before the period;
    *count* is how many counted transactions fall inside it.
    """
    start_cash = opening_balance + earlier_net
    net = sum(line.actual for line in lines)
    planned = sum(figures(line.amount, line.actual).remaining for line in lines)
    return Forecast(start_cash, planned, net, count, start_cash + planned + net)
