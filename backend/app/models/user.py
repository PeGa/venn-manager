"""A household member and their credentials (BACKEND.md § 8)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UTCDateTime

USERNAME_MAX = 64
REAL_NAME_MAX = 128
AVATAR_COLORS = (
    "#d9c7a8",
    "#a9c7b6",
    "#c9bfe0",
    "#f0c9b8",
    "#bcd3e6",
    "#e6d9a3",
    "#c5dcc0",
)


class User(Base):
    """A member. Removal is soft (`is_removed`); the row stays for old records."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(USERNAME_MAX), unique=True)
    real_name: Mapped[str] = mapped_column(String(REAL_NAME_MAX))
    password_hash: Mapped[str] = mapped_column(String(255))
    must_change_password: Mapped[bool] = mapped_column(Boolean)
    is_admin: Mapped[bool] = mapped_column(Boolean)
    language: Mapped[str | None] = mapped_column(String(2))
    theme: Mapped[str] = mapped_column(String(6))
    color: Mapped[str] = mapped_column(String(7))
    is_removed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
