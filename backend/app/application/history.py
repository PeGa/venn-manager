"""History: read-only past months (BACKEND.md § 4.6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from app.application.common import period
from app.application.transactions import TransactionView, view
from app.domain.errors import not_found
from app.domain.history import (
    Breakdown,
    HistoryFilter,
    MonthTotals,
    Slice,
    month_bounds,
    month_key,
    percent,
)
from app.domain.members import MemberView, member_view
from app.ports import Context


@dataclass(frozen=True)
class CategoryFacet:
    """A category chip; deleted categories still filter past months."""

    budget_id: UUID
    name: str
    deleted: bool


@dataclass(frozen=True)
class Facets:
    """Everything the History filter chips offer."""

    categories: list[CategoryFacet]
    members: list[MemberView]


def months(
    ctx: Context, filters: HistoryFilter, offset: int, limit: int
) -> tuple[list[MonthTotals], int]:
    """Past months with at least one match, newest first, and their count."""
    start = period(ctx).start
    totals = {
        (y, m): rows for y, m, rows, _, _ in ctx.uow.transactions.months_before(start)
    }
    found = [
        MonthTotals(month_key(y, m), rows, totals[(y, m)], spent, earned)
        for y, m, rows, spent, earned in ctx.uow.transactions.months_before(
            start, filters
        )
    ]
    return found[offset : offset + limit], len(found)


def _past_month(ctx: Context, key: str) -> tuple[date, date]:
    bounds = month_bounds(key)
    if bounds is None or bounds[1] >= period(ctx).start:
        raise not_found()
    return bounds


def month_transactions(
    ctx: Context, key: str, filters: HistoryFilter, offset: int, limit: int
) -> tuple[list[TransactionView], int]:
    """One page of a past month's transactions, newest first."""
    start, end = _past_month(ctx, key)
    txs = ctx.uow.transactions
    rows = txs.page(start, end, offset, limit, filters)
    current = period(ctx)
    return [view(t, b, current) for t, b in rows], txs.count(start, end, filters)


def breakdown(ctx: Context, key: str, filters: HistoryFilter) -> Breakdown:
    """Spending by category for the "Details…" pie, filters applied."""
    start, end = _past_month(ctx, key)
    spending = ctx.uow.transactions.spending_by_budget(start, end, filters)
    spent = sum(amount for _, _, amount in spending)
    rows = ctx.uow.transactions.months_before(end + timedelta(days=1), filters, start)
    earned = rows[0][4] if rows else 0
    slices = [
        Slice(b, name, amount, percent(amount, spent)) for b, name, amount in spending
    ]
    return Breakdown(key, spent, earned, slices)


def facets(ctx: Context) -> Facets:
    """Categories and members that appear in past months."""
    start = period(ctx).start
    categories = [
        CategoryFacet(b.id, b.name, b.is_deleted)
        for b in ctx.uow.budgets.used_before(start)
    ]
    members = [member_view(m, 0) for m in ctx.uow.members.used_before(start)]
    return Facets(categories, members)
