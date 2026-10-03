"""Coming up: scheduled budgets not yet done this period (BACKEND.md § 5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from app.domain.budgets import Schedule
from app.domain.period import Period

SOON_DAYS = 3
STEP_DAYS = {"weekly": 7, "biweekly": 14}


@dataclass(frozen=True)
class Scheduled:
    """A non-deleted budget with a schedule, and its actual this period."""

    budget_id: UUID
    name: str
    amount: int
    actual: int
    schedule: Schedule


@dataclass(frozen=True)
class UpcomingItem:
    """One row of Coming up (API_SURFACE.md § 1.6)."""

    budget_id: UUID
    name: str
    due_date: date
    amount: int
    actual: int
    soon: bool
    overdue: bool


def occurrences(schedule: Schedule, period: Period) -> list[date]:
    """Due dates of *schedule* inside *period*, in order."""
    anchor = schedule.anchor
    if schedule.repeat == "once":
        return [anchor] if period.contains(anchor) else []
    if schedule.repeat == "monthly":
        if (period.start.year, period.start.month) < (anchor.year, anchor.month):
            return []
        return [period.start.replace(day=min(anchor.day, period.days_in_month))]
    step = STEP_DAYS[schedule.repeat]
    skipped = max(0, -(-(period.start - anchor).days // step))
    day = anchor + timedelta(days=skipped * step)
    days = []
    while day <= period.end:
        days.append(day)
        day += timedelta(days=step)
    return days


def is_done(amount: int, actual: int) -> bool:
    """Whether the actual has reached the amount in its direction."""
    return actual >= amount if amount > 0 else actual <= amount


def _item(entry: Scheduled, period: Period) -> UpcomingItem | None:
    days = occurrences(entry.schedule, period)
    if entry.amount == 0 or not days or is_done(entry.amount, entry.actual):
        return None
    ahead = [day for day in days if day >= period.today]
    due = ahead[0] if ahead else days[-1]
    overdue = not ahead
    soon = overdue or (due - period.today).days <= SOON_DAYS
    return UpcomingItem(
        entry.budget_id, entry.name, due, entry.amount, entry.actual, soon, overdue
    )


def upcoming(entries: list[Scheduled], period: Period) -> list[UpcomingItem]:
    """Coming up for *period*, sorted by due date, then name."""
    items = [item for entry in entries if (item := _item(entry, period))]
    return sorted(items, key=lambda item: (item.due_date, item.name))
