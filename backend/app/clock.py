"""The source of "now". Injected so tests can freeze time (AGENTS.md § TDD)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Anything that can tell the current instant."""

    def now(self) -> datetime:
        """Return the current instant as an aware UTC datetime."""
        ...


class SystemClock:
    """The real clock."""

    def now(self) -> datetime:
        """Return the current instant as an aware UTC datetime."""
        return datetime.now(UTC)
