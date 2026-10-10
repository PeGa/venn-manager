"""The forecast (BACKEND.md § 4.3, § 4.4, § 4.7)."""

from app.domain.forecast import BudgetLine, forecast

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
    result = forecast(0, 0, [BudgetLine(-20000, -5000)], count=3)
    assert result.planned == -15000
    assert result.transaction_count == 3


def test_forecast_with_mixed_real_and_planned_money_reports_what_is_left() -> None:
    """Income 100 real; gigs +50, +30 planned; −10, −30 real; −5 planned → 135."""
    lines = [
        BudgetLine(100, 100),
        BudgetLine(50, 0),
        BudgetLine(30, 0),
        BudgetLine(-10, -10),
        BudgetLine(-30, -30),
        BudgetLine(-5, 0),
    ]
    assert forecast(0, 0, lines, count=3).total == 135
