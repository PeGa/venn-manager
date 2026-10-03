"""Household settings (API_SURFACE.md § 4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.activity import record
from app.application.auth import Auth
from app.application.common import commit_mutation, period
from app.domain.activity import Target
from app.domain.errors import validation
from app.domain.household import is_valid_timezone
from app.domain.members import MemberView, member_view
from app.ports import Context

CURRENCY = Target("settings", section="currency")
HOUSEHOLD = Target("settings", section="household")


@dataclass(frozen=True)
class HouseholdView:
    """Settings plus every member (API_SURFACE.md § 1.3)."""

    name: str
    currency_sign: str
    timezone: str
    opening_balance: int
    show_member_income: bool
    members: list[MemberView]


@dataclass(frozen=True)
class HouseholdChanges:
    """Fields to change. `None` means "leave as is"."""

    name: str | None = None
    currency_sign: str | None = None
    timezone: str | None = None
    opening_balance: int | None = None
    show_member_income: bool | None = None


# field → (activity action, params key, target)
ACTIVITY = {
    "name": ("settings.name", "name", HOUSEHOLD),
    "currency_sign": ("settings.currency", "sign", CURRENCY),
    "timezone": ("settings.timezone", "timezone", HOUSEHOLD),
    "opening_balance": ("settings.openingBalance", "amount", HOUSEHOLD),
    "show_member_income": ("settings.memberIncome", "enabled", HOUSEHOLD),
}


def household_view(ctx: Context) -> HouseholdView:
    """The household with every member's spend this period."""
    household = ctx.uow.household.get()
    current = period(ctx)
    spent = ctx.uow.transactions.spent_by_member(current.start, current.end)
    return HouseholdView(
        name=household.name,
        currency_sign=household.currency_sign,
        timezone=household.timezone,
        opening_balance=household.opening_balance,
        show_member_income=household.show_member_income,
        members=[member_view(m, spent.get(m.id, 0)) for m in ctx.uow.members.all()],
    )


def update_household(
    ctx: Context, auth: Auth, changes: HouseholdChanges
) -> HouseholdView:
    """Apply *changes*. Each field that actually changes writes one entry."""
    if changes.timezone is not None and not is_valid_timezone(changes.timezone):
        raise validation("Unknown time zone", "timezone")
    household = ctx.uow.household.get()
    for field, (action, key, target) in ACTIVITY.items():
        value: Any = getattr(changes, field)
        if value is None or value == getattr(household, field):
            continue
        setattr(household, field, value)
        record(ctx, auth.member.id, action, {key: value}, target)
    commit_mutation(ctx)
    return household_view(ctx)
