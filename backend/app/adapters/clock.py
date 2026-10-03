"""`Clock` port backed by the system time."""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    """The real clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)
