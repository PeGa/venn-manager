"""Recording activity entries (BACKEND.md § 9)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.domain.activity import Target, merges_into
from app.domain.entities import Activity
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
