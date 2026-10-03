"""Request dependencies: database, clock, period and the signed-in member."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.auth.sessions import COOKIE_NAME, find_session
from app.config import Settings
from app.db import get_db
from app.errors import AppError
from app.models import AuthSession, User
from app.services.household import period_for
from app.services.period import Period


@dataclass(frozen=True)
class Auth:
    """The member behind the request and the session they used."""

    user: User
    session: AuthSession


def get_settings(request: Request) -> Settings:
    """The app settings."""
    settings: Settings = request.app.state.settings
    return settings


def get_now(request: Request) -> datetime:
    """The current instant from the injected clock."""
    now: datetime = request.app.state.clock.now()
    return now


def get_period(
    db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> Period:
    """The current period."""
    return period_for(db, now)


def authenticated(request: Request, db: Session = Depends(get_db)) -> Auth:
    """Any valid session, even one that must change its password."""
    token = request.cookies.get(COOKIE_NAME)
    found = find_session(db, token) if token else None
    if found is None:
        raise AppError(401, "UNAUTHORIZED", "No active session")
    return Auth(user=found[1], session=found[0])


def member(auth: Auth = Depends(authenticated)) -> Auth:
    """A session allowed to use the app (BACKEND.md § 8.4)."""
    if auth.user.must_change_password:
        raise AppError(403, "PASSWORD_CHANGE_REQUIRED", "Password change required")
    return auth


def admin(auth: Auth = Depends(member)) -> Auth:
    """A session of an admin (BACKEND.md § 8.1)."""
    if not auth.user.is_admin:
        raise AppError(403, "FORBIDDEN", "Admins only")
    return auth
