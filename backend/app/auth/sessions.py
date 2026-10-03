"""Server-side session storage (BACKEND.md § 8.5)."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AuthSession, User

COOKIE_NAME = "venn_session"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User, now: datetime) -> str:
    """Store a new session for *user* and return the cookie token."""
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=_hash(token), user_id=user.id, created_at=now))
    return token


def find_session(db: Session, token: str) -> tuple[AuthSession, User] | None:
    """The session and member behind *token*, unless unknown or removed."""
    row = db.execute(
        select(AuthSession, User)
        .join(User, User.id == AuthSession.user_id)
        .where(AuthSession.token_hash == _hash(token), User.is_removed.is_(False))
    ).first()
    return None if row is None else (row[0], row[1])


def delete_sessions(
    db: Session, user_id: uuid.UUID, keep: uuid.UUID | None = None
) -> None:
    """Delete every session of *user_id*, except the one with id *keep*."""
    statement = delete(AuthSession).where(AuthSession.user_id == user_id)
    if keep is not None:
        statement = statement.where(AuthSession.id != keep)
    db.execute(statement)
