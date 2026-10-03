"""The household: the single row of shared settings (BACKEND.md § 1)."""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Boolean, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

HOUSEHOLD_NAME_MAX = 60
CURRENCY_SIGN_MAX = 8


class Household(Base):
    """Shared settings plus the ledger revision counter (BACKEND.md § 10)."""

    __tablename__ = "household"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(HOUSEHOLD_NAME_MAX))
    currency_sign: Mapped[str] = mapped_column(String(CURRENCY_SIGN_MAX))
    timezone: Mapped[str] = mapped_column(String(64))
    opening_balance: Mapped[int] = mapped_column(BigInteger)
    show_member_income: Mapped[bool] = mapped_column(Boolean)
    rev: Mapped[int] = mapped_column(Integer)
