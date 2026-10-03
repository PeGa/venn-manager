"""Setting model — generic key/value store for global and per-user settings.

`user_id IS NULL` marks a global setting (API_SURFACE.md reference schema).
There is no database unique constraint on (key, user_id): both SQLite and
PostgreSQL treat NULLs as distinct, so such a constraint would not actually
protect global rows. Uniqueness is enforced by the upsert in
`app.services.settings` instead.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base

SETTING_KEY_MAX_LENGTH = 64


class Setting(Base):
    """A single configuration value, global or owned by one user."""

    __tablename__ = "settings"
    __table_args__ = (Index("ix_settings_key_user_id", "key", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(SETTING_KEY_MAX_LENGTH), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    requires_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
