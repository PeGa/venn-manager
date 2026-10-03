"""The current period: the calendar month containing today (BACKEND.md § 3)."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Period:
    """The month every "this month" figure refers to."""

    month: str
    start: date
    end: date
    today: date
    days_in_month: int

    def contains(self, day: date) -> bool:
        """Whether *day* falls inside the period."""
        return self.start <= day <= self.end


def current_period(timezone: str, now: datetime) -> Period:
    """The period containing *now* as seen from *timezone*."""
    today = now.astimezone(ZoneInfo(timezone)).date()
    days = calendar.monthrange(today.year, today.month)[1]
    start = today.replace(day=1)
    return Period(
        month=f"{today.year:04d}-{today.month:02d}",
        start=start,
        end=start + timedelta(days=days - 1),
        today=today,
        days_in_month=days,
    )
