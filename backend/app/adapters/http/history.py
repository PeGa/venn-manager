"""`/history` routes, read-only (API_SURFACE.md § 9)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.adapters.http.deps import get_ctx, member
from app.adapters.http.shapes import (
    ApiModel,
    MemberOut,
    Page,
    PageParams,
    page_params,
)
from app.adapters.http.transactions import TransactionOut
from app.application import history as use_cases
from app.application.auth import Auth
from app.domain.history import HistoryFilter
from app.domain.transactions import PAYEE_MAX
from app.ports import Context

router = APIRouter(prefix="/history", tags=["history"])


def history_filter(
    q: str | None = Query(None, max_length=PAYEE_MAX),
    member_id: UUID | None = Query(None, alias="memberId"),
    budget_id: UUID | None = Query(None, alias="budgetId"),
) -> HistoryFilter:
    """Read `?q&memberId&budgetId`. A blank search means no search."""
    return HistoryFilter((q or "").strip() or None, member_id, budget_id)


class HistoryMonthOut(ApiModel):
    month: str
    match_count: int
    total_count: int
    spent: int
    earned: int


class SliceOut(ApiModel):
    budget_id: UUID
    category: str
    amount: int
    pct: int


class BreakdownOut(ApiModel):
    month: str
    spent: int
    earned: int
    slices: list[SliceOut]


class CategoryFacetOut(ApiModel):
    budget_id: UUID
    name: str
    deleted: bool


class FacetsOut(ApiModel):
    categories: list[CategoryFacetOut]
    members: list[MemberOut]


@router.get("/months")
def list_months(
    filters: HistoryFilter = Depends(history_filter),
    params: PageParams = Depends(page_params),
    _auth: Auth = Depends(member),
    ctx: Context = Depends(get_ctx),
) -> Page[HistoryMonthOut]:
    found, total = use_cases.months(ctx, filters, params.offset, params.size)
    return Page[HistoryMonthOut](
        items=[HistoryMonthOut.model_validate(m) for m in found],
        page=params.page,
        size=params.size,
        total=total,
    )


@router.get("/months/{month}/transactions")
def month_transactions(
    month: str,
    filters: HistoryFilter = Depends(history_filter),
    params: PageParams = Depends(page_params),
    _auth: Auth = Depends(member),
    ctx: Context = Depends(get_ctx),
) -> Page[TransactionOut]:
    views, total = use_cases.month_transactions(
        ctx, month, filters, params.offset, params.size
    )
    return Page[TransactionOut](
        items=[TransactionOut.model_validate(v) for v in views],
        page=params.page,
        size=params.size,
        total=total,
    )


@router.get("/months/{month}/breakdown")
def month_breakdown(
    month: str,
    filters: HistoryFilter = Depends(history_filter),
    _auth: Auth = Depends(member),
    ctx: Context = Depends(get_ctx),
) -> BreakdownOut:
    return BreakdownOut.model_validate(use_cases.breakdown(ctx, month, filters))


@router.get("/facets")
def history_facets(
    _auth: Auth = Depends(member), ctx: Context = Depends(get_ctx)
) -> FacetsOut:
    return FacetsOut.model_validate(use_cases.facets(ctx))
