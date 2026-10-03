"""User management rules (API_SURFACE.md § 3.2, BACKEND.md § 5.3).

Two invariants are absolute and enforced here rather than in the routes:
no account may delete itself, and the last remaining administrator may neither
be deleted nor demoted.
"""

from __future__ import annotations

from sqlalchemy import func, select

from app.extensions import DbSession
from app.models import User
from app.services.errors import conflict, forbidden, gone, not_found
from app.services.sessions import bump_epoch

LAST_ADMIN_MESSAGE = "Cannot delete the last administrator or your own account"
USERNAME_TAKEN_MESSAGE = "Username already taken"
NOT_FOUND_MESSAGE = "User not found"


def list_active_users(session: DbSession) -> list[User]:
    """Return every non-deleted user, ordered by id (creation order)."""
    return list(
        session.scalars(
            select(User).where(User.is_deleted.is_(False)).order_by(User.id)
        ).all()
    )


def count_admins(session: DbSession) -> int:
    """Count non-deleted administrators."""
    total = session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.is_admin.is_(True), User.is_deleted.is_(False))
    )
    return int(total or 0)


def is_last_admin(session: DbSession, user: User) -> bool:
    """True when *user* is the only administrator left."""
    return user.is_admin and count_admins(session) <= 1


def username_taken(session: DbSession, username: str) -> bool:
    """True when any row holds *username*, soft-deleted ones included.

    API_SURFACE.md § User Soft-Delete: a deleted user's username stays reserved.
    """
    return session.scalar(select(User.id).where(User.username == username)) is not None


def get_active_user(session: DbSession, user_id: int) -> User:
    """Load a user for a write, mapping absence and deletion onto contract codes."""
    user = session.get(User, user_id)
    if user is None:
        raise not_found(NOT_FOUND_MESSAGE)
    if user.is_deleted:
        raise gone()
    return user


def create_user(
    session: DbSession,
    *,
    username: str,
    real_name: str,
    password: str,
    is_admin: bool,
) -> User:
    """Create a user. Flushes; the caller commits."""
    if username_taken(session, username):
        raise conflict(USERNAME_TAKEN_MESSAGE)
    user = User.create(
        username=username, real_name=real_name, password=password, is_admin=is_admin
    )
    session.add(user)
    session.flush()
    return user


def update_user(
    session: DbSession,
    *,
    target: User,
    real_name: str | None = None,
    password: str | None = None,
    is_admin: bool | None = None,
) -> User:
    """Apply the allowed admin edits. Flushes; the caller commits.

    A password reset also bumps the target's session epoch, so a credential an
    admin had to replace cannot keep being used from an existing cookie.
    """
    if is_admin is False and target.is_admin and is_last_admin(session, target):
        raise forbidden(LAST_ADMIN_MESSAGE)
    if real_name is not None:
        target.real_name = real_name
    if is_admin is not None:
        target.is_admin = is_admin
    if password is not None:
        target.set_password(password)
        bump_epoch(session, target.id)
    session.flush()
    return target


def soft_delete_user(session: DbSession, *, actor: User, target: User) -> None:
    """Soft-delete a user and kill their sessions. Flushes; the caller commits.

    The row is kept so historical records still resolve a `user_id`
    (BACKEND.md § 5.3).
    """
    if target.id == actor.id or is_last_admin(session, target):
        raise forbidden(LAST_ADMIN_MESSAGE)
    target.is_deleted = True
    bump_epoch(session, target.id)
    session.flush()
