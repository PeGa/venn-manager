"""Budget model — a standing planned amount for a concept.

Budgets persist across months. Their `date` is informational (the intended day
of the money movement) and is never rewritten by the month switch; the frontend
displays it inside the working month with the day clamped (BACKEND.md § 3.4).
`amount` is nullable: a budget entry may exist without a reserved amount.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base
from app.utils.dates import utc_now


class Budget(Base):
    """A planned amount. Soft-deleted, never hard-deleted."""

    __tablename__ = "budgets"
    __table_args__ = (
        Index("ix_budgets_date", "date"),
        Index("ix_budgets_concept_id", "concept_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
