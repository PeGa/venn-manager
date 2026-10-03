"""A signed movement of money against one budget (BACKEND.md § 7)."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UTCDateTime

PAYEE_MAX = 120


class Transaction(Base):
    """Positive amounts come in, negative amounts go out. Never zero."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    payee: Mapped[str] = mapped_column(String(PAYEE_MAX))
    budget_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("budgets.id"), index=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[dt.datetime] = mapped_column(UTCDateTime)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
