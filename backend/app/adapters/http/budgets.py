"""`/budgets` routes (API_SURFACE.md § 6)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import StrictBool

from app.adapters.http.deps import get_ctx, member
from app.adapters.http.shapes import (
    ApiModel,
    Cents,
    InputModel,
    IsoDate,
    PeriodOut,
    provided,
    trimmed,
)
from app.application import budgets as use_cases
from app.application.auth import Auth
from app.application.budgets import BudgetChanges, BudgetView
from app.domain.budgets import BUDGET_NAME_MAX, Schedule
from app.ports import Context

router = APIRouter(prefix="/budgets", tags=["budgets"])

BudgetName = Annotated[str, trimmed(BUDGET_NAME_MAX)]


class ScheduleIO(InputModel):
    repeat: Literal["once", "weekly", "biweekly", "monthly"]
    anchor: IsoDate


class ScheduleOut(ApiModel):
    repeat: str
    anchor: date


class BudgetOut(ApiModel):
    id: UUID
    name: str
    amount: int
    schedule: ScheduleOut | None
    goal: bool
    created_at: datetime
    actual: int
    projected: int
    remaining: int
    over: bool
    over_by: int
    progress_pct: float

    @classmethod
    def of(cls, view: BudgetView) -> BudgetOut:
        """Flatten a budget view and its figures."""
        return cls(
            id=view.id,
            name=view.name,
            amount=view.amount,
            schedule=ScheduleOut.model_validate(view.schedule)
            if view.schedule
            else None,
            goal=view.goal,
            created_at=view.created_at,
            actual=view.figures.actual,
            projected=view.figures.projected,
            remaining=view.figures.remaining,
            over=view.figures.over,
            over_by=view.figures.over_by,
            progress_pct=view.figures.progress_pct,
        )


class BudgetListOut(ApiModel):
    period: PeriodOut
    items: list[BudgetOut]


class BudgetIn(InputModel):
    name: BudgetName


class BudgetPatchIn(InputModel):
    name: BudgetName | None = None
    amount: Cents | None = None
    schedule: ScheduleIO | None = None
    goal: StrictBool | None = None


@router.get("")
def list_budgets(
    _auth: Auth = Depends(member), ctx: Context = Depends(get_ctx)
) -> BudgetListOut:
    current, views = use_cases.list_budgets(ctx)
    return BudgetListOut(
        period=PeriodOut.model_validate(current),
        items=[BudgetOut.of(view) for view in views],
    )


@router.post("", status_code=201)
def create_budget(
    body: BudgetIn, auth: Auth = Depends(member), ctx: Context = Depends(get_ctx)
) -> BudgetOut:
    return BudgetOut.of(use_cases.create_budget(ctx, auth, body.name))


@router.patch("/{budget_id}")
def update_budget(
    budget_id: UUID,
    body: BudgetPatchIn,
    auth: Auth = Depends(member),
    ctx: Context = Depends(get_ctx),
) -> BudgetOut:
    sent = provided(body, nullable=("schedule",))
    schedule = body.schedule
    changes = BudgetChanges(
        name=body.name,
        amount=body.amount,
        goal=body.goal,
        schedule=Schedule(schedule.repeat, schedule.anchor) if schedule else None,
        schedule_sent="schedule" in sent,
    )
    return BudgetOut.of(use_cases.update_budget(ctx, auth, budget_id, changes))


@router.delete("/{budget_id}", status_code=204)
def delete_budget(
    budget_id: UUID, auth: Auth = Depends(member), ctx: Context = Depends(get_ctx)
) -> None:
    use_cases.delete_budget(ctx, auth, budget_id)
