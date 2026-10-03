"""Household settings rules (API_SURFACE.md § 12)."""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

HOUSEHOLD_NAME_MAX = 60
CURRENCY_SIGN_MAX = 8


def is_valid_timezone(name: str) -> bool:
    """Whether *name* is an IANA time zone known to this system."""
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True
