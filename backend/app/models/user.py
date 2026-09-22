"""User model.

Represents an authenticated user of the system. Supports admin role,
per-user preferences (language, theme), and forced password change on first login.
"""

from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


class User(UserMixin, db.Model):  # type: ignore[name-defined]
    """Application user with authentication and preference fields.

    Attributes:
        id: Primary key.
        username: Unique login identifier.
        real_name: Display name.
        password_hash: Werkzeug hashed password. Never exposed via API.
        is_admin: Whether this user has administrator privileges.
        language: Per-user UI language code (default 'en').
        theme: Per-user theme preference ('light', 'dark', 'system').
        must_change_password: Gate flag set True on first-run seed.
        created_at: Timestamp of account creation.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    real_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    theme: Mapped[str] = mapped_column(String(10), default="system", nullable=False)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    concepts: Mapped[list["Concept"]] = relationship(  # noqa: F821
        "Concept", back_populates="created_by_user", lazy="select"
    )
    transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        "Transaction", back_populates="user", lazy="select"
    )
    budgets: Mapped[list["Budget"]] = relationship(  # noqa: F821
        "Budget", back_populates="user", lazy="select"
    )

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Serialize user to dict for API responses.

        Args:
            include_sensitive: If True, includes must_change_password.
                               Used only by GET /api/auth/me.

        Returns:
            Dict matching the contract UserObject shape.
        """
        result: dict = {
            "id": self.id,
            "username": self.username,
            "real_name": self.real_name,
            "is_admin": self.is_admin,
            "language": self.language,
            "theme": self.theme,
            "created_at": self.created_at.isoformat(),
        }
        if include_sensitive:
            result["must_change_password"] = self.must_change_password
        return result
