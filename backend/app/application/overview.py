"""The Overview screen and Coming up (BACKEND.md § 4.3, § 4.4, § 5)."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.activity import ActivityView, views
from app.application.budgets import schedule_of
from app.application.common import period
from app.application.transactions import TransactionView, view
from app.domain.forecast import (
    BudgetLine,
    BudgetTotals,
    Forecast,
    budget_totals,
    forecast,
)
from app.domain.period import Period
from app.domain.upcoming import Scheduled, UpcomingItem, upcoming
from app.ports import Context

RECENT_TRANSACTIONS = 4
RECENT_ACTIVITY = 5


@dataclass(frozen=True)
class OverviewView:
    """Everything the Overview screen shows (API_SURFACE.md § 8)."""

    period: Period
    currency_sign: str
    budget_totals: BudgetTotals
    forecast: Forecast
    upcoming: list[UpcomingItem]
    recent_transactions: list[TransactionView]
    activity: list[ActivityView]


def _lines_and_upcoming(
    ctx: Context, current: Period
) -> tuple[list[BudgetLine], list[UpcomingItem]]:
    budgets = ctx.uow.budgets.active()
    actuals = ctx.uow.transactions.actual_by_budget(current.start, current.end)
    lines = [BudgetLine(b.amount, actuals.get(b.id, 0), b.is_goal) for b in budgets]
    scheduled = [
        Scheduled(b.id, b.name, b.amount, actuals.get(b.id, 0), schedule)
        for b in budgets
        if (schedule := schedule_of(b)) is not None
    ]
    return lines, upcoming(scheduled, current)


def coming_up(ctx: Context) -> list[UpcomingItem]:
    """Scheduled budgets not yet done this period."""
    return _lines_and_upcoming(ctx, period(ctx))[1]


def overview(ctx: Context) -> OverviewView:
    """Totals, forecast, Coming up, latest transactions and latest activity."""
    current = period(ctx)
    household = ctx.uow.household.get()
    lines, items = _lines_and_upcoming(ctx, current)
    txs = ctx.uow.transactions
    month_forecast = forecast(
        household.opening_balance,
        txs.net_before(current.start),
        lines,
        txs.counted_between(current.start, current.end),
    )
    recent = txs.page(current.start, current.end, 0, RECENT_TRANSACTIONS)
    return OverviewView(
        period=current,
        currency_sign=household.currency_sign,
        budget_totals=budget_totals(lines),
        forecast=month_forecast,
        upcoming=items,
        recent_transactions=[view(t, b, current) for t, b in recent],
        activity=views(ctx, ctx.uow.activity.page(0, RECENT_ACTIVITY)),
    )
