"""Concept model — the fixed categories records reference.

`flow` is immutable after creation (API_SURFACE.md § PATCH concepts); that rule
is enforced in the service layer, and a CHECK constraint keeps the column to
the two legal values even for hand-written SQL.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base
from app.utils.dates import utc_now

CONCEPT_NAME_MAX_LENGTH = 64
FLOW_IN = "in"
FLOW_OUT = "out"
FLOWS = (FLOW_IN, FLOW_OUT)


class Concept(Base):
    """A named In/Out category. Soft-deleted, never hard-deleted."""

    __tablename__ = "concepts"
    __table_args__ = (
        CheckConstraint("flow IN ('in', 'out')", name="ck_concepts_flow"),
        Index("ix_concepts_name", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(CONCEPT_NAME_MAX_LENGTH), nullable=False)
    flow: Mapped[str] = mapped_column(String(3), nullable=False)
    # Column name follows the reference schema in API_SURFACE.md; the owning
    # user is resolved with an explicit join rather than a relationship.
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
