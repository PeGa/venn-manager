"""Shared query pieces over transactions (BACKEND.md § 4.1)."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.orm import Session

from app.models import Budget, Transaction


def counted() -> ColumnElement[bool]:
    """A transaction counts when neither it nor its budget is deleted.

    Queries using this must join `Budget` on `Transaction.budget_id`.
    """
    return and_(Transaction.is_deleted.is_(False), Budget.is_deleted.is_(False))


def spent_by_member(db: Session, start: date, end: date) -> dict[uuid.UUID, int]:
    """Money out per member between *start* and *end*, as positive cents."""
    rows = db.execute(
        select(Transaction.member_id, func.sum(-Transaction.amount))
        .join(Budget, Budget.id == Transaction.budget_id)
        .where(
            counted(),
            Transaction.amount < 0,
            Transaction.date.between(start, end),
        )
        .group_by(Transaction.member_id)
    ).all()
    return {member_id: int(total) for member_id, total in rows}
