"""A concept and its budget, stored as one row (BACKEND.md § 6)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UTCDateTime

BUDGET_NAME_MAX = 60
REPEATS = ("once", "weekly", "biweekly", "monthly")


class Budget(Base):
    """The name is the concept; amount, schedule and goal flag are the budget."""

    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(BUDGET_NAME_MAX), index=True)
    amount: Mapped[int] = mapped_column(BigInteger, default=0)
    schedule_repeat: Mapped[str | None] = mapped_column(String(8))
    schedule_anchor: Mapped[date | None] = mapped_column(Date)
    is_goal: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
