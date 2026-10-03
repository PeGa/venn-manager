"""Working-month state (API_SURFACE.md § 2, BACKEND.md § 1.4 and § 3).

The month switch is a state signal, not a data operation: acknowledging a new
month rewrites one setting and touches nothing else.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select

from app.extensions import DbSession
from app.models import Transaction
from app.services.errors import conflict
from app.services.settings import LAST_ACKNOWLEDGED_MONTH, working_month, write_setting
from app.utils.dates import month_key

ALREADY_CURRENT_MESSAGE = "Already on the current month"


def earliest_transaction_month(session: DbSession) -> str | None:
    """Return the month of the oldest non-deleted transaction, or None.

    Soft-deleted rows are excluded because a deleted record disappears from
    every view (BACKEND.md § 1.1). A transaction whose *concept* was deleted is
    still a real transaction, so it counts here.
    """
    oldest = session.scalar(
        select(func.min(Transaction.date)).where(Transaction.is_deleted.is_(False))
    )
    return month_key(oldest) if oldest is not None else None


def month_state(session: DbSession, *, user_id: int, today: date) -> dict[str, Any]:
    """Build the `GET /current-month` payload."""
    current = month_key(today)
    acknowledged = working_month(session, user_id, today)
    return {
        "current_month": current,
        "last_acknowledged_month": acknowledged,
        "needs_switch": current != acknowledged,
        "earliest_month": earliest_transaction_month(session),
    }


def acknowledge_month(
    session: DbSession, *, user_id: int, today: date
) -> dict[str, Any]:
    """Move the user's working month to the current one.

    Raises `409 CONFLICT` when there is nothing to switch. Flushes; the caller
    commits.
    """
    current = month_key(today)
    if working_month(session, user_id, today) == current:
        raise conflict(ALREADY_CURRENT_MESSAGE)
    write_setting(session, LAST_ACKNOWLEDGED_MONTH, current, user_id)
    return month_state(session, user_id=user_id, today=today)
