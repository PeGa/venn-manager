"""Member serialization and lookups (BACKEND.md § 4.5, § 8)."""

from __future__ import annotations

from typing import cast

from sqlalchemy.orm import Session

from app.models import User
from app.schemas.members import (
    Language,
    MemberOut,
    PreferencesOut,
    SessionOut,
    Theme,
)
from app.services.ledger import spent_by_member
from app.services.period import Period


def member_out(user: User, spent: int) -> MemberOut:
    """Shape *user* for the API, with their spend this period."""
    return MemberOut(
        id=user.id,
        username=user.username,
        real_name=user.real_name,
        initial=user.real_name[:1].upper(),
        color=user.color,
        role="admin" if user.is_admin else "member",
        status="removed" if user.is_removed else "active",
        spent_this_month=spent,
    )


def session_out(db: Session, user: User, period: Period) -> SessionOut:
    """The `Session` body returned by login, session and `PATCH /me`."""
    spent = spent_by_member(db, period.start, period.end).get(user.id, 0)
    return SessionOut(
        member=member_out(user, spent),
        must_change_password=user.must_change_password,
        preferences=PreferencesOut(
            language=cast(Language | None, user.language),
            theme=cast(Theme, user.theme),
        ),
    )
