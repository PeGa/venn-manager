"""Transaction model.

Represents an actual money movement (income or spending) recorded on the Home screen.
Flow is derived from the associated Concept, not stored on this model.
Deletion is hard — no soft delete.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


class Transaction(db.Model):  # type: ignore[name-defined]
    """Actual money movement record.

    Attributes:
        id: Primary key.
        date: Transaction date (YYYY-MM-DD).
        concept_id: FK to Concept. Flow is derived from this.
        amount: Fixed-precision decimal amount.
        user_id: FK to User who recorded this transaction.
        created_at: Timestamp of creation.
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    concept_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("concepts.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    concept: Mapped["Concept"] = relationship(  # noqa: F821
        "Concept", back_populates="transactions", lazy="select"
    )
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="transactions", lazy="select"
    )

    def to_dict(self) -> dict:
        """Serialize transaction to dict for API responses.

        Flow is derived from the associated Concept.

        Returns:
            Dict matching the contract TransactionObject shape.
        """
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "concept_id": self.concept_id,
            "concept_name": self.concept.name if self.concept else None,
            "flow": self.concept.flow if self.concept else None,
            "amount": float(self.amount),
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "created_at": self.created_at.isoformat(),
        }
