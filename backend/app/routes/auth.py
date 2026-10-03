"""Auth endpoints — API_SURFACE.md § 1.

| Method | Route          | Auth | Purpose                                    |
|--------|----------------|------|--------------------------------------------|
| POST   | /auth/login    | no   | Authenticate and set the session cookie    |
| POST   | /auth/logout   | yes  | Invalidate the session server-side         |
| GET    | /auth/session  | yes  | Report the current session state           |
| POST   | /auth/password | yes  | Change own password; the only route a       |
|        |                |      | force-change session may call              |

Every response uses the standard envelope. Error codes: `UNAUTHORIZED` (401),
`PASSWORD_CHANGE_REQUIRED` (403), `VALIDATION_ERROR` (422).
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, request, session as flask_session
from flask_login import login_user, logout_user

from app.extensions import db
from app.middleware.auth import (
    EPOCH_CLAIM,
    MUST_CHANGE_CLAIM,
    authenticated_user,
    login_required,
)
from app.middleware.requests import json_body
from app.middleware.responses import respond
from app.models.user import USERNAME_MAX_LENGTH
from app.services.auth import (
    INVALID_CREDENTIALS_MESSAGE,
    authenticate,
    change_password,
    requires_password_change,
)
from app.services.errors import unauthorized
from app.services.serializers import serialize_user
from app.services.sessions import bump_epoch, current_epoch
from app.utils.validation import MAX_PASSWORD_LENGTH, require_string

auth_bp = Blueprint("auth", __name__)


def _session_payload() -> dict[str, Any]:
    """Build the payload shared by the login and session endpoints."""
    user = authenticated_user()
    return {
        "user": serialize_user(user),
        "must_change_password": bool(flask_session.get(MUST_CHANGE_CLAIM, False)),
    }


@auth_bp.post("/auth/login")
def login() -> Any:
    """Authenticate a user.

    Request: `{"username": str, "password": str}`.
    Response 200: `{"user": {...}, "must_change_password": bool}` plus a session
    cookie. Errors: 401 `UNAUTHORIZED` (bad credentials, unknown user, or a
    soft-deleted user — all indistinguishable), 422 `VALIDATION_ERROR`.
    """
    payload = json_body(request)
    username = require_string(payload, "username", max_length=USERNAME_MAX_LENGTH)
    # Passwords are never trimmed: surrounding whitespace is part of the secret.
    password = require_string(
        payload, "password", max_length=MAX_PASSWORD_LENGTH, strip=False
    )

    user = authenticate(db.session, username, password)
    if user is None:
        raise unauthorized(INVALID_CREDENTIALS_MESSAGE)

    default_password = str(current_app.config["DEFAULT_ADMIN_PASSWORD"])
    force_change = requires_password_change(
        db.session, user, default_password=default_password
    )
    login_user(user)
    # Bind this cookie to the user's live epoch so a later logout or password
    # change invalidates it server-side.
    flask_session[EPOCH_CLAIM] = current_epoch(db.session, user.id)
    flask_session[MUST_CHANGE_CLAIM] = force_change
    return respond(_session_payload())


@auth_bp.post("/auth/logout")
@login_required
def logout() -> Any:
    """End the session.

    Response 200: `data: null`. The user's epoch is incremented first, so any
    cookie that is still in circulation stops resolving to a user.
    Errors: 401 `UNAUTHORIZED`, 403 `PASSWORD_CHANGE_REQUIRED`.
    """
    user = authenticated_user()
    bump_epoch(db.session, user.id)
    db.session.commit()
    flask_session.clear()
    logout_user()
    return respond()


@auth_bp.get("/auth/session")
@login_required
def get_session() -> Any:
    """Report the current session state.

    Response 200: same shape as a successful login.
    Errors: 401 `UNAUTHORIZED`, 403 `PASSWORD_CHANGE_REQUIRED`.
    """
    return respond(_session_payload())


@auth_bp.post("/auth/password")
@login_required
def password() -> Any:
    """Change the calling user's password.

    Request: `{"current_password": str, "new_password": str}`.
    Response 200: `data: null`. The caller's own session survives; every other
    session for that user is invalidated.
    Errors: 401 `UNAUTHORIZED` (wrong current password), 422 `VALIDATION_ERROR`
    (too short, too long, or unchanged).
    """
    user = authenticated_user()
    payload = json_body(request)
    current_password = require_string(
        payload, "current_password", max_length=MAX_PASSWORD_LENGTH, strip=False
    )
    new_password = require_string(
        payload, "new_password", max_length=MAX_PASSWORD_LENGTH, strip=False
    )

    change_password(
        db.session,
        user,
        current_password=current_password,
        new_password=new_password,
    )
    new_epoch = bump_epoch(db.session, user.id)
    db.session.commit()

    # Re-issue this session against the new epoch and lift the force-change gate.
    flask_session[EPOCH_CLAIM] = new_epoch
    flask_session[MUST_CHANGE_CLAIM] = False
    return respond()
