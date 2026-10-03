"""Left to spend and the forecast (BACKEND.md § 4.3, § 4.4, § 4.7)."""

from app.domain.forecast import BudgetLine, budget_totals, forecast

PAYCHECK, GROCERIES, CAR, RENT = 100, -10, -30, -20


def _lines(paycheck: int = 0, groceries: int = 0) -> list[BudgetLine]:
    return [
        BudgetLine(PAYCHECK, paycheck),
        BudgetLine(GROCERIES, groceries),
        BudgetLine(CAR, 0),
        BudgetLine(RENT, 0),
    ]


def test_worked_example_from_backend_contract() -> None:
    """BACKEND.md § 4.7, row by row."""
    steps = [
        ("Month starts", _lines(), 0, 40, 40),
        ("Groceries −5", _lines(groceries=-5), -5, 45, 40),
        ("Groceries −25 more", _lines(groceries=-30), -30, 50, 20),
        ("Paycheck +100", _lines(paycheck=100, groceries=-30), 70, -50, 20),
    ]
    for label, lines, net, planned, total in steps:
        result = forecast(opening_balance=0, earlier_net=0, lines=lines, count=0)
        assert (result.transactions_net, result.planned, result.total) == (
            net,
            planned,
            total,
        ), label
    next_month = forecast(opening_balance=0, earlier_net=70, lines=_lines(), count=0)
    assert next_month.start_cash == 70


def test_forecast_with_spend_inside_budget_keeps_total() -> None:
    before = forecast(0, 0, [BudgetLine(-1000, 0)], 0).total
    after = forecast(0, 0, [BudgetLine(-1000, -400)], 1).total
    assert before == after == -1000


def test_forecast_start_cash_adds_opening_balance_and_earlier_months() -> None:
    result = forecast(opening_balance=500, earlier_net=-200, lines=[], count=0)
    assert result.start_cash == 300
    assert result.total == 300


def test_forecast_counts_goals_and_reports_transaction_count() -> None:
    result = forecast(0, 0, [BudgetLine(-20000, -5000, goal=True)], count=3)
    assert result.planned == -15000
    assert result.transaction_count == 3


def test_budget_totals_ignore_goals_and_income() -> None:
    totals = budget_totals(
        [
            BudgetLine(-80000, -60400),
            BudgetLine(-35000, -31600),
            BudgetLine(224000, 224000),
            BudgetLine(-20000, -20000, goal=True),
        ]
    )
    assert (totals.limit, totals.spent, totals.left_to_spend) == (115000, 92000, 23000)
    assert totals.spent_pct == 80.0


def test_budget_totals_count_spending_against_zero_budgets() -> None:
    totals = budget_totals([BudgetLine(-160000, -120300), BudgetLine(0, -202600)])
    assert totals.limit == 160000
    assert totals.spent == 322900
    assert totals.left_to_spend == -162900
    assert totals.spent_pct == 100.0


def test_budget_totals_ignore_refunds_and_income_on_zero_budgets() -> None:
    totals = budget_totals([BudgetLine(-1000, 300), BudgetLine(0, 500)])
    assert (totals.spent, totals.left_to_spend) == (0, 1000)


def test_budget_totals_without_limits_has_zero_percent() -> None:
    assert budget_totals([]).spent_pct == 0.0
