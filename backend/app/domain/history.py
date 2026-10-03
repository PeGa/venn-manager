"""History: past months, filters and the spending breakdown (BACKEND.md § 4.6)."""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date
from uuid import UUID

MONTH_KEY = re.compile(r"(\d{4})-(\d{2})")


@dataclass(frozen=True)
class HistoryFilter:
    """Shared filters. `q` matches payee, category or member name, any case."""

    q: str | None = None
    member_id: UUID | None = None
    budget_id: UUID | None = None


@dataclass(frozen=True)
class MonthTotals:
    """One past month (API_SURFACE.md § 1.9)."""

    month: str
    match_count: int
    total_count: int
    spent: int
    earned: int


@dataclass(frozen=True)
class Slice:
    """One category of the spending pie."""

    budget_id: UUID
    category: str
    amount: int
    pct: int


@dataclass(frozen=True)
class Breakdown:
    """The "Details…" pie of one month."""

    month: str
    spent: int
    earned: int
    slices: list[Slice]


def month_key(year: int, month: int) -> str:
    """`YYYY-MM`."""
    return f"{year:04d}-{month:02d}"


def month_bounds(key: str) -> tuple[date, date] | None:
    """First and last day of month *key*, or `None` when it is not `YYYY-MM`."""
    match = MONTH_KEY.fullmatch(key)
    if match is None or not 1 <= int(match[2]) <= 12:
        return None
    year, month = int(match[1]), int(match[2])
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def percent(part: int, total: int) -> int:
    """`round_half_up(part / total × 100)` in integer arithmetic."""
    if total == 0:
        return 0
    return (part * 200 + total) // (2 * total)
