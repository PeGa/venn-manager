"""Date and month arithmetic.

Pure functions over stdlib types: no Flask, no SQLAlchemy, no HTTP. The month
helpers implement CONTRACTS/BACKEND.md § 3 (Month Switch Mechanics) and
§ 1.4 (The Working Month), which is why they are isolated here rather than
inlined in routes or services.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timezone

MONTH_FORMAT_LENGTH = 7  # "YYYY-MM"


def utc_now() -> datetime:
    """Return the current UTC time as a naive datetime.

    Naive-UTC is the storage convention: SQLite cannot persist offsets, so
    keeping every timestamp naive and UTC avoids a mixed representation.
    Serialisation adds the `Z` (see app.utils.json.format_timestamp).
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def month_key(value: date) -> str:
    """Render a date as its `YYYY-MM` month identifier."""
    return f"{value.year:04d}-{value.month:02d}"


def month_bounds(month: str) -> tuple[date, date]:
    """Return the inclusive first and last day of a `YYYY-MM` month."""
    year, _, raw_month = month.partition("-")
    parsed_year = int(year)
    parsed_month = int(raw_month)
    last_day = calendar.monthrange(parsed_year, parsed_month)[1]
    return date(parsed_year, parsed_month, 1), date(parsed_year, parsed_month, last_day)


def previous_month(month: str) -> str:
    """Return the `YYYY-MM` immediately before *month*."""
    year, _, raw_month = month.partition("-")
    parsed_year, parsed_month = int(year), int(raw_month)
    if parsed_month == 1:
        return f"{parsed_year - 1:04d}-12"
    return f"{parsed_year:04d}-{parsed_month - 1:02d}"


def next_month(month: str) -> str:
    """Return the `YYYY-MM` immediately after *month*."""
    year, _, raw_month = month.partition("-")
    parsed_year, parsed_month = int(year), int(raw_month)
    if parsed_month == 12:
        return f"{parsed_year + 1:04d}-01"
    return f"{parsed_year:04d}-{parsed_month + 1:02d}"


def is_before(left: str, right: str) -> bool:
    """Return True when month *left* is strictly earlier than month *right*.

    `YYYY-MM` is lexicographically ordered, so a string comparison is exact and
    avoids parsing on every call.
    """
    return left < right
