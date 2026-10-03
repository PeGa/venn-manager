"""Informational activity feed entries (BACKEND.md § 9)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UTCDateTime


class Activity(Base):
    """Who did what, with a snapshot of the names involved. Never deleted."""

    __tablename__ = "activity"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(32))
    params: Mapped[dict[str, Any]] = mapped_column(JSON)
    target_type: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    target_section: Mapped[str | None] = mapped_column(String(16))
    at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
