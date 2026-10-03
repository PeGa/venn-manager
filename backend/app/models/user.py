"""User model.

`must_change_password` is intentionally absent: API_SURFACE.md § Force Password
Change derives it at login from the password hash and the user count, so there
is no column to keep in sync.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import Base
from app.utils.dates import utc_now

USERNAME_MAX_LENGTH = 64
REAL_NAME_MAX_LENGTH = 128

#: werkzeug's default method, as AGENTS.md § Authentication & Session Security
#: requires. Named explicitly rather than left implicit so the choice is visible
#: and so the test suite can lower the work factor without changing algorithm.
#: werkzeug expands the bare name to scrypt n=32768, r=8, p=1.
HASH_METHOD = "scrypt"


class User(Base):
    """An account in the shared wallet. Soft-deleted, never hard-deleted."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # UNIQUE also reserves the username of a soft-deleted user, which is what
    # API_SURFACE.md § User Soft-Delete requires.
    username: Mapped[str] = mapped_column(
        String(USERNAME_MAX_LENGTH), unique=True, nullable=False
    )
    real_name: Mapped[str] = mapped_column(String(REAL_NAME_MAX_LENGTH), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    @classmethod
    def create(
        cls,
        *,
        username: str,
        password: str,
        real_name: str | None = None,
        is_admin: bool = False,
    ) -> User:
        """Build an unsaved user with a hashed password.

        The hash method is :data:`HASH_METHOD`, per AGENTS.md § Authentication
        & Session Security.
        """
        return cls(
            username=username,
            real_name=real_name if real_name is not None else username,
            password_hash=generate_password_hash(password, method=HASH_METHOD),
            is_admin=is_admin,
        )

    def set_password(self, password: str) -> None:
        """Replace the stored hash. Also lifts a derived force-change state."""
        self.password_hash = generate_password_hash(password, method=HASH_METHOD)

    def verify_password(self, password: str) -> bool:
        """Return True when *password* matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    # --- Flask-Login user protocol -------------------------------------
    # Implemented directly instead of inheriting `UserMixin`, which ships no
    # type information; subclassing it fails mypy --strict.

    @property
    def is_active(self) -> bool:
        """Whether the account may hold a session. Deleted accounts may not."""
        return not self.is_deleted

    @property
    def is_authenticated(self) -> bool:
        """Always true for a persisted user; the anonymous proxy is not one."""
        return True

    @property
    def is_anonymous(self) -> bool:
        """Always false for a persisted user."""
        return False

    def get_id(self) -> str:
        """Return the identifier Flask-Login stores in the session."""
        return str(self.id)
