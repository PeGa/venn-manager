"""The projection engine (BACKEND.md § 2, API_SURFACE.md § Projection Calculation).

Split in two on purpose:

* :func:`compute_projections` is the domain rule — pure arithmetic over
  pre-aggregated totals, with no Flask, no SQLAlchemy and no HTTP. It is what
  the contract's pseudocode describes, and it is unit-tested directly.
* :func:`month_projections` is the repository adapter — it turns the inclusion
  rules of BACKEND.md § 2.1 into two grouped SQL queries so no record set is
  ever loaded into memory (AGENTS.md § Performance Guardrails).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.extensions import DbSession
from app.models import Budget, Concept, Transaction
from app.models.concept import FLOW_IN, FLOW_OUT
from app.utils.dates import is_before, month_bounds

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


@dataclass(frozen=True)
class BudgetTotal:
    """Summed active budget amount for one concept. `None` means only nulls."""

    concept_id: int
    flow: str
    amount: Decimal | None


@dataclass(frozen=True)
class TransactionTotal:
    """Summed active transaction amount for one concept in the target month."""

    concept_id: int
    flow: str
    amount: Decimal
    concept_is_deleted: bool


def compute_projections(
    budgets: Sequence[BudgetTotal],
    transactions: Sequence[TransactionTotal],
    *,
    history: bool,
) -> dict[str, Decimal]:
    """Apply the projection formula (BACKEND.md § 2.2).

    `max` and `min` compare a plan against an outcome, so a budgeted concept with
    no transactions in the month projects its budget — there is no outcome to
    compare yet. That is not the same as an actual of zero: a recorded `0`
    transaction *is* an actual and is compared normally.

    Once transactions exist, spending is pessimistic (`max`: an overspend shows,
    an underspend still assumes the budget will be reached) and earning is
    pessimistic the other way (`min`: a shortfall shows, a windfall is capped so
    the projection never inflates). Concepts with no budget contribute their
    transactions in full as unbudgeted activity.
    """
    counted = [
        entry for entry in transactions if history or not entry.concept_is_deleted
    ]
    budget_by_concept = _sum_budgets(budgets)
    flow_by_concept = {entry.concept_id: entry.flow for entry in budgets}
    actual_by_concept = _sum_transactions(counted)

    spend = ZERO
    earn = ZERO
    spend_remaining = ZERO
    earn_remaining = ZERO
    for concept_id, budgeted in budget_by_concept.items():
        # A missing key means no transactions at all, which must stay distinct
        # from a recorded zero. Coercing it to ZERO here is the defect that made
        # earn_projection report a shortfall that had not happened.
        actual = actual_by_concept.get(concept_id)
        if flow_by_concept[concept_id] == FLOW_OUT:
            contribution = budgeted if actual is None else max(budgeted, actual)
            spend += contribution
            # The part of this concept's projection that has not been spent yet.
            spend_remaining += contribution - (ZERO if actual is None else actual)
        else:
            earn += budgeted if actual is None else min(budgeted, actual)
            earn_remaining += (
                budgeted if actual is None else max(budgeted - actual, ZERO)
            )

    for entry in counted:
        if entry.concept_id in budget_by_concept:
            continue
        if entry.flow == FLOW_OUT:
            spend += entry.amount
        else:
            earn += entry.amount

    actual_spend = sum(
        (entry.amount for entry in counted if entry.flow == FLOW_OUT), ZERO
    )
    actual_earn = sum(
        (entry.amount for entry in counted if entry.flow == FLOW_IN), ZERO
    )
    return {
        "spend_projection": _quantise(spend),
        "earn_projection": _quantise(earn),
        "savings_projection": _quantise(earn - spend),
        "actual_spend": _quantise(actual_spend),
        "actual_earn": _quantise(actual_earn),
        # BACKEND.md § 2.4: the unspent / unbooked part of each projection, so the
        # UI can explain why a projection differs from the actuals.
        "spend_budget_remaining": _quantise(spend_remaining),
        "earn_budget_remaining": _quantise(earn_remaining),
    }


def month_projections(
    session: DbSession, *, month: str, working_month: str
) -> dict[str, Decimal]:
    """Compute projections for *month* as seen by a user working in *working_month*.

    A month strictly before the working month is history: transactions of a
    deleted concept stay in the totals as unbudgeted activity, so the past is
    never rewritten (BACKEND.md § 1.2). Their budgets never count either way.
    """
    history = is_before(month, working_month)
    first_day, last_day = month_bounds(month)
    return compute_projections(
        _budget_totals(session),
        _transaction_totals(session, first_day, last_day, history=history),
        history=history,
    )


def _budget_totals(session: DbSession) -> list[BudgetTotal]:
    """Active budgets of live concepts, grouped per concept, across all months.

    Budgets persist and their dates are informational, so no month filter is
    applied (API_SURFACE.md § GET /records). `SUM` ignores NULL amounts, which
    is exactly the "null counts as 0" rule; a concept whose budgets are all
    null sums to None and is treated as zero.
    """
    rows = session.execute(
        select(Budget.concept_id, Concept.flow, func.sum(Budget.amount))
        .join(Concept, Budget.concept_id == Concept.id)
        .where(Budget.is_deleted.is_(False), Concept.is_deleted.is_(False))
        .group_by(Budget.concept_id, Concept.flow)
    ).all()
    return [BudgetTotal(concept_id, flow, amount) for concept_id, flow, amount in rows]


def _transaction_totals(
    session: DbSession, first_day: date, last_day: date, *, history: bool
) -> list[TransactionTotal]:
    """Active transactions inside the month, grouped per concept."""
    conditions = [
        Transaction.is_deleted.is_(False),
        Transaction.date >= first_day,
        Transaction.date <= last_day,
    ]
    if not history:
        conditions.append(Concept.is_deleted.is_(False))
    rows = session.execute(
        select(
            Transaction.concept_id,
            Concept.flow,
            func.sum(Transaction.amount),
            Concept.is_deleted,
        )
        .join(Concept, Transaction.concept_id == Concept.id)
        .where(*conditions)
        .group_by(Transaction.concept_id, Concept.flow, Concept.is_deleted)
    ).all()
    return [
        TransactionTotal(concept_id, flow, amount, bool(concept_is_deleted))
        for concept_id, flow, amount, concept_is_deleted in rows
    ]


def _sum_budgets(budgets: Sequence[BudgetTotal]) -> dict[int, Decimal]:
    totals: dict[int, Decimal] = {}
    for entry in budgets:
        previous = totals.get(entry.concept_id, ZERO)
        totals[entry.concept_id] = previous + (entry.amount or ZERO)
    return totals


def _sum_transactions(
    transactions: Sequence[TransactionTotal],
) -> dict[int, Decimal]:
    totals: dict[int, Decimal] = {}
    for entry in transactions:
        totals[entry.concept_id] = totals.get(entry.concept_id, ZERO) + entry.amount
    return totals


def _quantise(value: Decimal) -> Decimal:
    """Normalise to two decimal places so the wire format is always `x.yy`."""
    return value.quantize(TWO_PLACES)
