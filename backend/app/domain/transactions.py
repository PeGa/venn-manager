"""Transaction rules (BACKEND.md § 3, § 7)."""

from __future__ import annotations

from datetime import date

from app.domain.entities import Budget, Transaction
from app.domain.errors import DomainError, validation
from app.domain.period import Period

PAYEE_MAX = 120
BULK_DELETE_MAX = 500


def is_archived(day: date, period: Period) -> bool:
    """A transaction before the current period belongs to History."""
    return day < period.start


def require_amount(amount: int) -> None:
    """Transactions move money; zero is not a movement."""
    if amount == 0:
        raise validation("Amount must not be zero", "amount")


def require_in_period(day: date, period: Period) -> None:
    """New and edited transactions stay inside the current month."""
    if not period.contains(day):
        raise DomainError("OUT_OF_PERIOD", "Date outside the current month", "date")


def require_writable(transaction: Transaction, budget: Budget, period: Period) -> None:
    """Archived rows and rows of a deleted budget are read-only."""
    if is_archived(transaction.date, period):
        raise DomainError("READ_ONLY_HISTORY", "Past months are read-only")
    if budget.is_deleted:
        raise DomainError("CATEGORY_DELETED", "This transaction's budget was deleted")
