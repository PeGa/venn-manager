"""Authentication rules (API_SURFACE.md § 1 and § Force Password Change).

No Flask imports: the caller supplies the session and the configured default
password, so these rules are testable without an HTTP request.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import DbSession
from app.models import User, user as user_model
from app.services.errors import unauthorized, validation_error
from app.utils.validation import validate_password

INVALID_CREDENTIALS_MESSAGE = "Invalid username or password"
INVALID_CURRENT_PASSWORD_MESSAGE = "Invalid current password"


@lru_cache(maxsize=1)
def _decoy_hash() -> str:
    """A throwaway hash, verified against when the lookup cannot succeed.

    Without it, a request for an unknown username returns much faster than one
    for a real username with a wrong password, which lets an attacker enumerate
    accounts by timing.
    """
    # Read through the module, not by value, so the test suite can lower the
    # work factor for the decoy exactly as it does for real hashes.
    return generate_password_hash("decoy-password", method=user_model.HASH_METHOD)


def authenticate(session: DbSession, username: str, password: str) -> User | None:
    """Return the user matching *username* and *password*, or None.

    A soft-deleted user never authenticates and is indistinguishable from an
    unknown one (API_SURFACE.md § POST /auth/login).
    """
    user: User | None = session.scalar(select(User).where(User.username == username))
    if user is None or user.is_deleted:
        check_password_hash(_decoy_hash(), password)
        return None
    if not user.verify_password(password):
        return None
    return user


def count_active_users(session: DbSession) -> int:
    """Count non-deleted users."""
    total = session.scalar(
        select(func.count()).select_from(User).where(User.is_deleted.is_(False))
    )
    return int(total or 0)


def requires_password_change(
    session: DbSession, user: User, *, default_password: str
) -> bool:
    """Derive the force-change condition. There is no stored flag.

    API_SURFACE.md § Force Password Change: the account's password still equals
    the seeded default **and** it is the only active user.
    """
    if not user.verify_password(default_password):
        return False
    return count_active_users(session) == 1


def change_password(
    session: DbSession, user: User, *, current_password: str, new_password: str
) -> None:
    """Validate and apply a password change. Flushes; the caller commits."""
    if not user.verify_password(current_password):
        raise unauthorized(INVALID_CURRENT_PASSWORD_MESSAGE)
    validate_password(new_password)
    if new_password == current_password:
        raise validation_error("New password must differ from the current password")
    user.set_password(new_password)
    session.flush()
