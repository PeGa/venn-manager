"""`/auth`: login, logout, session, password (API_SURFACE.md § 2)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Auth, authenticated, get_now, get_period, get_settings, member
from app.auth.passwords import hash_password, verify_password
from app.auth.sessions import COOKIE_NAME, create_session, delete_sessions
from app.config import Settings
from app.db import get_db
from app.errors import AppError, validation
from app.models import User
from app.schemas.common import InputModel, Password
from app.schemas.members import SessionOut
from app.services.members import session_out
from app.services.period import Period

router = APIRouter(prefix="/auth", tags=["auth"])

Credential = Annotated[str, StringConstraints(strict=True, max_length=256)]


class LoginIn(InputModel):
    username: Credential
    password: Credential


class PasswordIn(InputModel):
    current_password: Credential
    new_password: Password


@router.post("/login")
def login(
    body: LoginIn,
    response: Response,
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
    period: Period = Depends(get_period),
    settings: Settings = Depends(get_settings),
) -> SessionOut:
    """Start a session. Removed members and wrong passwords get the same 401."""
    user = db.scalars(
        select(User).where(User.username == body.username, User.is_removed.is_(False))
    ).first()
    if user is None or not verify_password(user.password_hash, body.password):
        raise AppError(401, "UNAUTHORIZED", "Invalid username or password")
    token = create_session(db, user, now)
    db.commit()
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
        path="/",
    )
    return session_out(db, user, period)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    auth: Auth = Depends(authenticated),
    db: Session = Depends(get_db),
) -> None:
    """End this session only. Allowed during a forced password change."""
    db.delete(auth.session)
    db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/session")
def session(
    auth: Auth = Depends(member),
    db: Session = Depends(get_db),
    period: Period = Depends(get_period),
) -> SessionOut:
    """The signed-in member."""
    return session_out(db, auth.user, period)


@router.post("/password", status_code=204)
def change_password(
    body: PasswordIn,
    auth: Auth = Depends(authenticated),
    db: Session = Depends(get_db),
) -> None:
    """Set a new password, clear the forced-change flag, end other sessions."""
    if not verify_password(auth.user.password_hash, body.current_password):
        raise validation("Current password is wrong", "currentPassword")
    auth.user.password_hash = hash_password(body.new_password)
    auth.user.must_change_password = False
    delete_sessions(db, auth.user.id, keep=auth.session.id)
    db.commit()
