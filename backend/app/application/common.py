"""Helpers every use case shares."""

from __future__ import annotations

from app.domain.period import Period, current_period
from app.ports import Context


def period(ctx: Context) -> Period:
    """The current period in the household's time zone (BACKEND.md § 3)."""
    return current_period(ctx.uow.household.get().timezone, ctx.clock.now())


def commit_mutation(ctx: Context) -> None:
    """Bump the revision and commit in one transaction (BACKEND.md § 10)."""
    ctx.uow.household.get().rev += 1
    ctx.uow.commit()
