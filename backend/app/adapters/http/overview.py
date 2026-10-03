"""`/overview`, `/upcoming`, `/activity` and `/balance` (API_SURFACE.md § 8, § 10)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import field_serializer

from app.adapters.http.deps import get_ctx, member
from app.adapters.http.shapes import ApiModel, Page, PageParams, PeriodOut, page_params
from app.adapters.http.transactions import TransactionOut
from app.application.activity import TargetView, list_activity
from app.application.auth import Auth
from app.application.balance import balance
from app.application.overview import coming_up, overview
from app.ports import Context

router = APIRouter(tags=["overview"])


class UpcomingOut(ApiModel):
    budget_id: UUID
    name: str
    due_date: date
    amount: int
    actual: int
    soon: bool
    overdue: bool


class ActivityOut(ApiModel):
    id: UUID
    actor_id: UUID
    action: str
    params: dict[str, Any]
    at: datetime
    target: TargetView

    @field_serializer("target")
    def _target(self, target: TargetView) -> dict[str, object]:
        """Only the fields of the target's variant (API_SURFACE.md § 1.8)."""
        fields = {
            "type": target.type,
            "id": str(target.id) if target.id else None,
            "section": target.section,
            "archived": target.archived,
            "month": target.month,
            "goal": target.goal,
        }
        return {key: value for key, value in fields.items() if value is not None}


class BudgetTotalsOut(ApiModel):
    limit: int
    spent: int
    left_to_spend: int
    spent_pct: float


class ForecastOut(ApiModel):
    start_cash: int
    planned: int
    transactions_net: int
    transaction_count: int
    total: int


class OverviewOut(ApiModel):
    period: PeriodOut
    currency_sign: str
    budget_totals: BudgetTotalsOut
    forecast: ForecastOut
    upcoming: list[UpcomingOut]
    recent_transactions: list[TransactionOut]
    activity: list[ActivityOut]


class MemberIncomeOut(ApiModel):
    member_id: UUID
    month_in: int
    all_time_in: int


class BalanceOut(ApiModel):
    balance: int
    month_in: int
    month_out: int
    members: list[MemberIncomeOut] | None


@router.get("/overview")
def get_overview(
    _auth: Auth = Depends(member), ctx: Context = Depends(get_ctx)
) -> OverviewOut:
    return OverviewOut.model_validate(overview(ctx))


@router.get("/upcoming")
def get_upcoming(
    _auth: Auth = Depends(member), ctx: Context = Depends(get_ctx)
) -> list[UpcomingOut]:
    return [UpcomingOut.model_validate(item) for item in coming_up(ctx)]


@router.get("/activity")
def get_activity(
    params: PageParams = Depends(page_params),
    _auth: Auth = Depends(member),
    ctx: Context = Depends(get_ctx),
) -> Page[ActivityOut]:
    entries, total = list_activity(ctx, params.offset, params.size)
    return Page[ActivityOut](
        items=[ActivityOut.model_validate(e) for e in entries],
        page=params.page,
        size=params.size,
        total=total,
    )


@router.get("/balance")
def get_balance(
    _auth: Auth = Depends(member), ctx: Context = Depends(get_ctx)
) -> BalanceOut:
    return BalanceOut.model_validate(balance(ctx))
