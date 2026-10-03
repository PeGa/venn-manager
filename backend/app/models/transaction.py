"""Transaction model — an actual money movement in a given month."""

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


class Transaction(Base):
    """A recorded spend or earning. Soft-deleted, never hard-deleted."""

    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_date", "date"),
        Index("ix_transactions_concept_id", "concept_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"), nullable=False)
    # DECIMAL(10,2) per the API_SURFACE.md reference schema.
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
