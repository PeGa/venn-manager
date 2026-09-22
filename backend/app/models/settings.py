"""Settings model.

Singleton table storing global application settings.
Currently holds only the currency symbol (1 grapheme cluster).
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class Settings(db.Model):  # type: ignore[name-defined]
    """Global application settings (single-row table).

    Attributes:
        id: Primary key.
        currency: Global currency symbol, exactly 1 grapheme cluster.
    """

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)

    def to_dict(self) -> dict:
        """Serialize settings to dict.

        Returns:
            Dict with the currency field.
        """
        return {"currency": self.currency}
