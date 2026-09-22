"""Budget model.

Represents a planned money movement for the current month.
Amount is nullable (user hasn't reserved a value yet).
Flow is derived from the associated Concept. Deletion is hard.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


class Budget(db.Model):  # type: ignore[name-defined]
    """Planned money movement for budgeting purposes.

    Attributes:
        id: Primary key.
        date: Target date for this budget entry (YYYY-MM-DD).
        concept_id: FK to Concept. Flow is derived from this.
        amount: Nullable fixed-precision decimal. None means no reserved value.
        user_id: FK to User who created this budget entry.
        created_at: Timestamp of creation.
    """

    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    concept_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("concepts.id"), nullable=False
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    concept: Mapped["Concept"] = relationship(  # noqa: F821
        "Concept", back_populates="budgets", lazy="select"
    )
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="budgets", lazy="select"
    )

    def to_dict(self) -> dict:
        """Serialize budget entry to dict for API responses.

        Flow is derived from the associated Concept.

        Returns:
            Dict matching the contract BudgetObject shape.
        """
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "concept_id": self.concept_id,
            "concept_name": self.concept.name if self.concept else None,
            "flow": self.concept.flow if self.concept else None,
            "amount": float(self.amount) if self.amount is not None else None,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "created_at": self.created_at.isoformat(),
        }
