"""Recording activity entries (BACKEND.md § 9)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.application.common import period
from app.domain.activity import Target, merges_into
from app.domain.entities import Activity
from app.domain.transactions import is_archived
from app.ports import Context


def record(
    ctx: Context, actor_id: UUID, action: str, params: dict[str, Any], target: Target
) -> None:
    """Add an entry, or update the newest one when the merge rule applies."""
    now = ctx.clock.now()
    newest = ctx.uow.activity.newest()
    if newest is not None and merges_into(newest, actor_id, action, target):
        newest.params = params
        newest.at = now
        return
    ctx.uow.activity.add(
        Activity(
            actor_id=actor_id,
            action=action,
            at=now,
            params=params,
            target_type=target.type,
            target_id=target.id,
            target_section=target.section,
        )
    )


@dataclass(frozen=True)
class TargetView:
    """Where an entry navigates to, resolved against the current state."""

    type: str
    id: UUID | None = None
    section: str | None = None
    archived: bool | None = None
    month: str | None = None
    goal: bool | None = None


@dataclass(frozen=True)
class ActivityView:
    """An entry as the API shows it (API_SURFACE.md § 1.8)."""

    id: UUID
    actor_id: UUID
    action: str
    params: dict[str, Any]
    at: datetime
    target: TargetView


NONE = TargetView("none")


def list_activity(
    ctx: Context, offset: int, limit: int
) -> tuple[list[ActivityView], int]:
    """A page of entries, newest first, and the total count."""
    entries = ctx.uow.activity.page(offset, limit)
    return views(ctx, entries), ctx.uow.activity.count()


def views(ctx: Context, entries: list[Activity]) -> list[ActivityView]:
    """Shape *entries*, resolving every target with one query per kind."""
    resolve = _resolver(ctx, entries)
    return [
        ActivityView(e.id, e.actor_id, e.action, e.params, e.at, resolve(e))
        for e in entries
    ]


def _ids(entries: list[Activity], kind: str) -> set[UUID]:
    return {e.target_id for e in entries if e.target_type == kind and e.target_id}


def _resolver(
    ctx: Context, entries: list[Activity]
) -> Callable[[Activity], TargetView]:
    current = period(ctx)
    found_tx = ctx.uow.transactions.get_many(_ids(entries, "transaction"))
    found_budgets = ctx.uow.budgets.get_many(_ids(entries, "budget"))
    found_members = ctx.uow.members.get_many(_ids(entries, "member"))

    def resolve(entry: Activity) -> TargetView:
        key = entry.target_id
        if entry.target_type == "settings":
            return TargetView("settings", section=entry.target_section)
        if entry.target_type == "transaction" and key in found_tx:
            tx = found_tx[key]
            if not tx.is_deleted:
                month = f"{tx.date.year:04d}-{tx.date.month:02d}"
                archived = is_archived(tx.date, current)
                return TargetView("transaction", key, archived=archived, month=month)
        if entry.target_type == "budget" and key in found_budgets:
            budget = found_budgets[key]
            if not budget.is_deleted:
                return TargetView("budget", key, goal=budget.is_goal)
        if entry.target_type == "member" and key in found_members:
            if not found_members[key].is_removed:
                return TargetView("member", key)
        return NONE

    return resolve
