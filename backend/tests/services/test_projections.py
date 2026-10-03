"""Unit tests for the pure projection maths (BACKEND.md § 2)."""

from __future__ import annotations

from decimal import Decimal

from app.services.projections import (
    BudgetTotal,
    TransactionTotal,
    compute_projections,
)

OUT = "out"
IN = "in"


def budget(concept_id: int, flow: str, amount: str | None) -> BudgetTotal:
    return BudgetTotal(
        concept_id=concept_id,
        flow=flow,
        amount=None if amount is None else Decimal(amount),
    )


def transaction(
    concept_id: int, flow: str, amount: str, deleted_concept: bool = False
) -> TransactionTotal:
    return TransactionTotal(
        concept_id=concept_id,
        flow=flow,
        amount=Decimal(amount),
        concept_is_deleted=deleted_concept,
    )


def compute(
    budgets: list[BudgetTotal],
    transactions: list[TransactionTotal],
    *,
    history: bool = False,
) -> dict[str, Decimal]:
    return compute_projections(budgets, transactions, history=history)


class TestSpendProjection:
    def test_budget_higher_than_actual_uses_the_budget(self) -> None:
        """BACKEND.md § 2.2: spending is pessimistic — max(budget, actual)."""
        result = compute([budget(1, OUT, "500.00")], [transaction(1, OUT, "200.00")])

        assert result["spend_projection"] == Decimal("500.00")

    def test_actual_higher_than_budget_uses_the_actual(self) -> None:
        result = compute([budget(1, OUT, "500.00")], [transaction(1, OUT, "830.50")])

        assert result["spend_projection"] == Decimal("830.50")

    def test_budget_with_no_activity_still_counts(self) -> None:
        """No transactions means no actual to compare, so the budget is projected."""
        result = compute([budget(1, OUT, "500.00")], [])

        assert result["spend_projection"] == Decimal("500.00")

    def test_recorded_zero_spend_still_projects_the_budget(self) -> None:
        """A recorded 0 *is* an actual; max(500, 0) is still the budget."""
        result = compute([budget(1, OUT, "500.00")], [transaction(1, OUT, "0.00")])

        assert result["spend_projection"] == Decimal("500.00")

    def test_out_fallback_is_explicit_not_a_max_coincidence(self) -> None:
        """A negative budget with no transactions projects the budget, not 0.

        `max(-50, 0)` would return 0, so this is the case that proves the OUT
        branch falls back deliberately rather than benefiting from the accident
        that coercing a missing actual to zero used to give the right answer.
        """
        result = compute([budget(1, OUT, "-50.00")], [])

        assert result["spend_projection"] == Decimal("-50.00")

    def test_unbudgeted_spending_is_added(self) -> None:
        """BACKEND.md § 2.3: activity outside the budget counts in full."""
        result = compute(
            [budget(1, OUT, "100.00")],
            [transaction(1, OUT, "50.00"), transaction(2, OUT, "30.00")],
        )

        assert result["spend_projection"] == Decimal("130.00")

    def test_several_budget_entries_for_one_concept_are_summed(self) -> None:
        result = compute([budget(1, OUT, "100.00"), budget(1, OUT, "50.00")], [])

        assert result["spend_projection"] == Decimal("150.00")

    def test_null_budget_amount_counts_as_zero(self) -> None:
        """BACKEND.md § 2.2: a budget without a reserved amount is 0."""
        result = compute([budget(1, OUT, None)], [transaction(1, OUT, "40.00")])

        assert result["spend_projection"] == Decimal("40.00")

    def test_null_budget_with_no_activity_is_zero(self) -> None:
        result = compute([budget(1, OUT, None)], [])

        assert result["spend_projection"] == Decimal("0.00")


class TestEarnProjection:
    def test_actual_below_budget_uses_the_actual(self) -> None:
        """BACKEND.md § 2.2: earning is pessimistic — min(budget, actual)."""
        result = compute([budget(1, IN, "3000.00")], [transaction(1, IN, "1200.00")])

        assert result["earn_projection"] == Decimal("1200.00")

    def test_actual_above_budget_caps_at_the_budget(self) -> None:
        result = compute([budget(1, IN, "3000.00")], [transaction(1, IN, "4500.00")])

        assert result["earn_projection"] == Decimal("3000.00")

    def test_budget_with_no_transactions_projects_the_budget(self) -> None:
        """BACKEND.md § 2.2: no actual yet is not an actual of zero.

        Without this, savings_projection is negative by the whole spend budget on
        the first day of every month, before any income could have arrived.
        """
        result = compute([budget(1, IN, "3000.00")], [])

        assert result["earn_projection"] == Decimal("3000.00")

    def test_recorded_zero_income_projects_zero(self) -> None:
        """A recorded 0 *is* an actual, so the budget no longer stands in for it."""
        result = compute([budget(1, IN, "3000.00")], [transaction(1, IN, "0.00")])

        assert result["earn_projection"] == Decimal("0.00")

    def test_partial_income_caps_at_the_actual(self) -> None:
        result = compute([budget(1, IN, "3000.00")], [transaction(1, IN, "1200.00")])

        assert result["earn_projection"] == Decimal("1200.00")

    def test_unbudgeted_earning_is_added(self) -> None:
        result = compute(
            [budget(1, IN, "1000.00")],
            [transaction(1, IN, "1000.00"), transaction(2, IN, "250.00")],
        )

        assert result["earn_projection"] == Decimal("1250.00")


class TestSavingsProjection:
    def test_is_earn_minus_spend(self) -> None:
        result = compute(
            [budget(1, OUT, "1250.00"), budget(2, IN, "3000.00")],
            [transaction(2, IN, "3000.00")],
        )

        assert result["savings_projection"] == Decimal("1750.00")

    def test_first_day_of_month_is_not_negative_by_the_whole_spend_budget(self) -> None:
        """The regression this amendment fixes: budgeted income, nothing booked yet."""
        result = compute([budget(1, OUT, "1250.00"), budget(2, IN, "3000.00")], [])

        assert result["earn_projection"] == Decimal("3000.00")
        assert result["spend_projection"] == Decimal("1250.00")
        assert result["savings_projection"] == Decimal("1750.00")

    def test_may_be_negative(self) -> None:
        result = compute([budget(1, OUT, "5000.00")], [])

        assert result["savings_projection"] == Decimal("-5000.00")


class TestActuals:
    def test_sums_the_months_transactions(self) -> None:
        result = compute(
            [],
            [
                transaction(1, OUT, "100.00"),
                transaction(2, OUT, "50.25"),
                transaction(3, IN, "900.00"),
            ],
        )

        assert result["actual_spend"] == Decimal("150.25")
        assert result["actual_earn"] == Decimal("900.00")

    def test_empty_month_is_all_zeros(self) -> None:
        result = compute([], [])

        assert result == {
            "spend_projection": Decimal("0.00"),
            "earn_projection": Decimal("0.00"),
            "savings_projection": Decimal("0.00"),
            "actual_spend": Decimal("0.00"),
            "actual_earn": Decimal("0.00"),
            "spend_budget_remaining": Decimal("0.00"),
            "earn_budget_remaining": Decimal("0.00"),
        }

    def test_deleted_concept_transactions_count_as_unbudgeted_in_history(self) -> None:
        """BACKEND.md § 1.2: previous months are never rewritten."""
        result = compute(
            [], [transaction(1, OUT, "70.00", deleted_concept=True)], history=True
        )

        assert result["spend_projection"] == Decimal("70.00")
        assert result["actual_spend"] == Decimal("70.00")


class TestDecimalHygiene:
    def test_no_binary_float_error(self) -> None:
        """FRONTEND.md: assume 0.1 + 0.2 = 0.3."""
        result = compute([], [transaction(1, OUT, "0.10"), transaction(2, OUT, "0.20")])

        assert result["actual_spend"] == Decimal("0.30")

    def test_results_never_exceed_two_decimal_places(self) -> None:
        """Money is DECIMAL(10,2) end to end; no float drift may leak out."""
        result = compute(
            [budget(1, OUT, "10.10")],
            [transaction(1, OUT, "0.20"), transaction(2, IN, "0.30")],
        )

        for value in result.values():
            exponent = value.as_tuple().exponent
            assert isinstance(exponent, int)
            assert -exponent <= 2


class TestBudgetRemaining:
    """The decomposition the UI shows under the projection widgets."""

    def test_spend_remaining_is_the_unspent_budget(self) -> None:
        result = compute([budget(1, OUT, "500.00")], [transaction(1, OUT, "200.00")])

        assert result["spend_budget_remaining"] == Decimal("300.00")
        # The identity API_SURFACE.md § 5 promises.
        assert (
            result["spend_projection"]
            == result["actual_spend"] + result["spend_budget_remaining"]
        )

    def test_spend_remaining_is_zero_once_the_budget_is_reached(self) -> None:
        result = compute([budget(1, OUT, "500.00")], [transaction(1, OUT, "830.50")])

        assert result["spend_budget_remaining"] == Decimal("0.00")

    def test_earn_remaining_is_the_unbooked_budget(self) -> None:
        result = compute([budget(1, IN, "3000.00")], [transaction(1, IN, "1200.00")])

        assert result["earn_budget_remaining"] == Decimal("1800.00")

    def test_earn_remaining_is_zero_when_income_exceeds_the_budget(self) -> None:
        """The cap drops the excess from the projection, so nothing is "expected"."""
        result = compute([budget(1, IN, "100.00")], [transaction(1, IN, "150.00")])

        assert result["earn_budget_remaining"] == Decimal("0.00")
        assert result["earn_projection"] == Decimal("100.00")

    def test_unbudgeted_activity_does_not_move_the_remaining(self) -> None:
        result = compute(
            [budget(1, OUT, "100.00")],
            [transaction(2, OUT, "30.00")],
        )

        assert result["spend_budget_remaining"] == Decimal("100.00")
        assert result["spend_projection"] == Decimal("130.00")

    def test_the_reported_case_decomposes_into_spent_plus_planned(self) -> None:
        """Budgets IN=100 / OUT=10, then OUT 3 (budgeted) and OUT 9 (unbudgeted).

        spend_projection 19 must read as 12 already spent + 7 of budget left.
        """
        result = compute(
            [budget(1, OUT, "10.00"), budget(3, IN, "100.00")],
            [transaction(1, OUT, "3.00"), transaction(2, OUT, "9.00")],
        )

        assert result["actual_spend"] == Decimal("12.00")
        assert result["spend_budget_remaining"] == Decimal("7.00")
        assert result["spend_projection"] == Decimal("19.00")
        assert result["earn_budget_remaining"] == Decimal("100.00")
        assert result["savings_projection"] == Decimal("81.00")
