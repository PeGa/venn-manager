"""Budgets and their concepts (BACKEND.md § 4.2, § 6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.activity import record
from app.application.auth import Auth
from app.application.common import commit_mutation, period
from app.domain.activity import Target
from app.domain.budgets import BudgetFigures, Schedule, figures
from app.domain.entities import Budget
from app.domain.errors import DomainError, gone, not_found
from app.domain.period import Period
from app.ports import Context


@dataclass(frozen=True)
class BudgetView:
    """A budget with its figures for the current period (API_SURFACE.md § 1.4)."""

    id: UUID
    name: str
    amount: int
    schedule: Schedule | None
    goal: bool
    created_at: datetime
    figures: BudgetFigures


@dataclass(frozen=True)
class BudgetChanges:
    """Fields to change. `None` means "leave as is".

    For `schedule`, `None` is meaningful ("clear it"), so `schedule_sent` says
    whether the field was sent at all.
    """

    name: str | None = None
    amount: int | None = None
    goal: bool | None = None
    schedule: Schedule | None = None
    schedule_sent: bool = False


def schedule_of(budget: Budget) -> Schedule | None:
    """The budget's schedule, if it has one."""
    if budget.schedule_repeat is None or budget.schedule_anchor is None:
        return None
    return Schedule(budget.schedule_repeat, budget.schedule_anchor)


def _views(budgets: list[Budget], actuals: dict[UUID, int]) -> list[BudgetView]:
    return [
        BudgetView(
            id=b.id,
            name=b.name,
            amount=b.amount,
            schedule=schedule_of(b),
            goal=b.is_goal,
            created_at=b.created_at,
            figures=figures(b.amount, actuals.get(b.id, 0)),
        )
        for b in budgets
    ]


def _view(ctx: Context, budget: Budget) -> BudgetView:
    current = period(ctx)
    actuals = ctx.uow.transactions.actual_by_budget(current.start, current.end)
    return _views([budget], actuals)[0]


def _active(ctx: Context, budget_id: UUID) -> Budget:
    budget = ctx.uow.budgets.get(budget_id)
    if budget is None:
        raise not_found()
    if budget.is_deleted:
        raise gone()
    return budget


def _require_free_name(ctx: Context, name: str, except_id: UUID | None = None) -> None:
    if ctx.uow.budgets.name_taken(name, except_id):
        raise DomainError("DUPLICATE_NAME", "Budget name already used", "name")


def list_budgets(ctx: Context) -> tuple[Period, list[BudgetView]]:
    """Every non-deleted budget, goals included, in creation order."""
    current = period(ctx)
    actuals = ctx.uow.transactions.actual_by_budget(current.start, current.end)
    return current, _views(ctx.uow.budgets.active(), actuals)


def create_budget(ctx: Context, auth: Auth, name: str) -> BudgetView:
    """Add a concept with a zero budget, no schedule, not a goal."""
    _require_free_name(ctx, name)
    budget = Budget(name=name, created_at=ctx.clock.now(), created_by=auth.member.id)
    ctx.uow.budgets.add(budget)
    record(
        ctx,
        auth.member.id,
        "budget.create",
        {"name": name},
        Target("budget", budget.id),
    )
    commit_mutation(ctx)
    return _view(ctx, budget)


def update_budget(
    ctx: Context, auth: Auth, budget_id: UUID, changes: BudgetChanges
) -> BudgetView:
    """Rename, set the amount, schedule or goal flag. One entry per real change."""
    budget = _active(ctx, budget_id)
    if changes.name is not None and changes.name != budget.name:
        _rename(ctx, auth, budget, changes.name)
    if changes.amount is not None and changes.amount != budget.amount:
        budget.amount = changes.amount
        _log(ctx, auth, budget, "budget.amount", amount=budget.amount)
    if changes.schedule_sent and changes.schedule != schedule_of(budget):
        budget.schedule_repeat = changes.schedule.repeat if changes.schedule else None
        budget.schedule_anchor = changes.schedule.anchor if changes.schedule else None
        _log(ctx, auth, budget, "budget.schedule")
    if changes.goal is not None and changes.goal != budget.is_goal:
        budget.is_goal = changes.goal
        _log(ctx, auth, budget, "budget.goal", goal=budget.is_goal)
    commit_mutation(ctx)
    return _view(ctx, budget)


def _rename(ctx: Context, auth: Auth, budget: Budget, name: str) -> None:
    _require_free_name(ctx, name, except_id=budget.id)
    old_name, budget.name = budget.name, name
    _log(ctx, auth, budget, "budget.rename", oldName=old_name)


def _log(
    ctx: Context, auth: Auth, budget: Budget, action: str, **extra: object
) -> None:
    params = {"name": budget.name, **extra}
    record(ctx, auth.member.id, action, params, Target("budget", budget.id))


def delete_budget(ctx: Context, auth: Auth, budget_id: UUID) -> None:
    """Soft-delete. Its transactions stay listed but stop counting (§ 4.1)."""
    budget = _active(ctx, budget_id)
    budget.is_deleted = True
    record(
        ctx,
        auth.member.id,
        "budget.delete",
        {"name": budget.name},
        Target("budget", budget.id),
    )
    commit_mutation(ctx)
