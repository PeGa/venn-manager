"""Concept model.

Represents an accounting concept (category) tied to a specific flow direction.
Concepts are soft-deleted to preserve referential integrity with transactions
and budget entries.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


class Concept(db.Model):  # type: ignore[name-defined]
    """Accounting concept (e.g. 'Groceries', 'Salary') tied to IN or OUT flow.

    Attributes:
        id: Primary key.
        name: Display name, max 64 chars.
        flow: 'IN' or 'OUT'. Immutable after creation.
        created_by: FK to User who created this concept.
        created_at: Timestamp of creation.
        is_deleted: Soft-delete flag.
    """

    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    flow: Mapped[str] = mapped_column(String(3), nullable=False)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_by_user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="concepts", lazy="select"
    )
    transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        "Transaction", back_populates="concept", lazy="select"
    )
    budgets: Mapped[list["Budget"]] = relationship(  # noqa: F821
        "Budget", back_populates="concept", lazy="select"
    )

    def to_dict(self) -> dict:
        """Serialize concept to dict for API responses.

        Returns:
            Dict matching the contract ConceptObject shape.
        """
        return {
            "id": self.id,
            "name": self.name,
            "flow": self.flow,
            "created_by": self.created_by,
            "username": self.created_by_user.username if self.created_by_user else None,
            "created_at": self.created_at.isoformat(),
        }
