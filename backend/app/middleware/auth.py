"""Auth gates: who may call an endpoint, and what a restricted session may do.

Three pieces, all HTTP-facing:

* the Flask-Login user loader, which rejects deleted users and stale sessions;
* `login_required` / `admin_required`, the per-endpoint gates from
  API_SURFACE.md § Endpoint Summary;
* the force-password-change `before_request` hook, which restricts a session
  derived as needing a new password to `POST /auth/password` alone.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import Flask, request, session as flask_session
from flask_login import current_user

from app.extensions import db, login_manager
from app.models import User
from app.services.errors import forbidden, password_change_required, unauthorized
from app.services.sessions import current_epoch

#: Claims this app writes into the Flask session. Prefixed to stay clear of
#: Flask-Login's own `_user_id`, `_fresh` and `_id` keys.
EPOCH_CLAIM = "venn_epoch"
MUST_CHANGE_CLAIM = "venn_must_change_password"

#: API_SURFACE.md § Force Password Change: a restricted session may call only
#: these. Login is exempt because it creates the restricted session, and logout
#: because a session that cannot end itself traps the user on the change screen
#: with no way to switch account.
GATE_EXEMPT_ENDPOINTS = frozenset(
    {"auth.login", "auth.password", "auth.logout", "static"}
)

ViewFunction = Callable[..., Any]


def _unwrap_current_user() -> Any:
    return current_user._get_current_object()


def authenticated_user() -> User:
    """Return the signed-in user, or raise `401 UNAUTHORIZED`."""
    user = _unwrap_current_user()
    if not isinstance(user, User) or user.is_deleted:
        raise unauthorized()
    return user


def require_admin() -> User:
    """Return the signed-in user, or raise `403 FORBIDDEN` for non-admins."""
    user = authenticated_user()
    if not user.is_admin:
        raise forbidden("Administrator role required")
    return user


def login_required(view: ViewFunction) -> ViewFunction:
    """Gate a view behind an authenticated session."""

    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        authenticated_user()
        return view(*args, **kwargs)

    return wrapper


def admin_required(view: ViewFunction) -> ViewFunction:
    """Gate a view behind the admin role (API_SURFACE.md § 3.2)."""

    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        require_admin()
        return view(*args, **kwargs)

    return wrapper


def load_user(user_id: str) -> User | None:
    """Resolve the session's user, rejecting deleted accounts and stale epochs.

    Returning None makes Flask-Login treat the request as anonymous, so every
    gated endpoint answers `401` — including a copied cookie replayed after the
    owner logged out.
    """
    try:
        identifier = int(user_id)
    except (TypeError, ValueError):
        return None
    user = db.session.get(User, identifier)
    if user is None or user.is_deleted:
        return None
    if flask_session.get(EPOCH_CLAIM) != current_epoch(db.session, user.id):
        return None
    return user


def enforce_password_change_gate() -> None:
    """Block a force-change session from everything except the password route.

    Runs before the view, so it also covers endpoints that have no auth gate of
    their own. Anonymous requests are left alone: `login_required` reports those.
    """
    if not flask_session.get(MUST_CHANGE_CLAIM):
        return None
    if request.endpoint in GATE_EXEMPT_ENDPOINTS:
        return None
    if isinstance(_unwrap_current_user(), User):
        raise password_change_required()
    return None


def init_auth(app: Flask) -> None:
    """Wire Flask-Login and the force-change gate into *app*."""
    login_manager.init_app(app)
    # This app validates sessions itself (epoch + is_deleted), so Flask-Login's
    # IP/user-agent heuristic must not silently downgrade or drop them.
    login_manager.session_protection = None
    login_manager.user_loader(load_user)
    app.before_request(enforce_password_change_gate)
