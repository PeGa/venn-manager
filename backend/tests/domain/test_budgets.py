"""Per-budget figures (BACKEND.md § 4.2)."""

import pytest

from app.domain.budgets import BudgetFigures, figures


@pytest.mark.parametrize(
    ("amount", "actual", "expected"),
    [
        # spending budget, within plan
        (-1000, -500, BudgetFigures(-500, -1000, -500, False, 0, 50.0)),
        # spending budget, exactly reached
        (-1000, -1000, BudgetFigures(-1000, -1000, 0, False, 0, 100.0)),
        # spending budget, overspent: actual replaces the plan
        (-1000, -3000, BudgetFigures(-3000, -3000, 0, True, 2000, 100.0)),
        # spending budget, only a refund so far
        (-1000, 200, BudgetFigures(200, -1000, -1200, False, 0, 0.0)),
        # income budget, nothing received yet
        (10000, 0, BudgetFigures(0, 10000, 10000, False, 0, 0.0)),
        # income budget, received more than planned
        (10000, 11000, BudgetFigures(11000, 11000, 0, True, 1000, 100.0)),
        # zero budget: projected is the actual
        (0, -202600, BudgetFigures(-202600, -202600, 0, True, 202600, 0.0)),
        (0, 0, BudgetFigures(0, 0, 0, False, 0, 0.0)),
    ],
)
def test_figures(amount: int, actual: int, expected: BudgetFigures) -> None:
    assert figures(amount, actual) == expected


def test_figures_paycheck_advance_nets_out() -> None:
    # BACKEND.md § 4.7: +10 advance, +100 pay, −10 repayment against +100.
    assert figures(10000, 1000).projected == 10000
    assert figures(10000, 11000).projected == 11000
    assert figures(10000, 10000).projected == 10000
