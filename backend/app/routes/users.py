"""User management — API_SURFACE.md § 3.2.

| Method | Route                 | Auth  | Purpose                     |
|--------|-----------------------|-------|-----------------------------|
| GET    | /settings/users       | admin | List non-deleted users      |
| POST   | /settings/users       | admin | Create a user               |
| PATCH  | /settings/users/:id   | admin | Edit real_name/password/is_admin |
| DELETE | /settings/users/:id   | admin | Soft-delete a user          |

Errors: 401 `UNAUTHORIZED`, 403 `FORBIDDEN` (non-admin, self-delete, last
admin) or `PASSWORD_CHANGE_REQUIRED`, 404 `NOT_FOUND`, 409 `CONFLICT`
(username taken), 410 `GONE` (already deleted), 422 `VALIDATION_ERROR`.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, request

from app.extensions import db
from app.middleware.auth import admin_required, authenticated_user
from app.middleware.requests import json_body
from app.middleware.responses import respond
from app.models.user import REAL_NAME_MAX_LENGTH, USERNAME_MAX_LENGTH
from app.services.errors import validation_error
from app.services.serializers import serialize_user
from app.services.users import (
    create_user,
    get_active_user,
    list_active_users,
    soft_delete_user,
    update_user,
)
from app.utils.validation import (
    MAX_PASSWORD_LENGTH,
    nullable_bool,
    optional_bool,
    optional_string,
    require_string,
    validate_password,
)

users_bp = Blueprint("users", __name__)

#: PATCH only touches these. `username` belongs to the profile keys on
#: `PATCH /settings` (API_SURFACE.md § 3.1), so submitting it here is an error.
EDITABLE_USER_FIELDS = frozenset({"real_name", "password", "is_admin"})

NO_FIELDS_MESSAGE = "At least one field must be provided"
UNKNOWN_FIELDS_MESSAGE = "Request contains unknown fields"


@users_bp.get("/settings/users")
@admin_required
def list_users() -> Any:
    """List every non-deleted user. Not paginated; `meta` is null."""
    return respond([serialize_user(user) for user in list_active_users(db.session)])


@users_bp.post("/settings/users")
@admin_required
def add_user() -> Any:
    """Create a user.

    Request: `{username, real_name, password, is_admin?}`. Response 201: the
    created user without any credential material.
    """
    payload = json_body(request)
    user = create_user(
        db.session,
        username=require_string(payload, "username", max_length=USERNAME_MAX_LENGTH),
        real_name=require_string(payload, "real_name", max_length=REAL_NAME_MAX_LENGTH),
        password=validate_password(
            require_string(
                payload, "password", max_length=MAX_PASSWORD_LENGTH, strip=False
            )
        ),
        is_admin=optional_bool(payload, "is_admin"),
    )
    db.session.commit()
    return respond(serialize_user(user), status=201)


@users_bp.patch("/settings/users/<int:user_id>")
@admin_required
def edit_user(user_id: int) -> Any:
    """Edit a user's real name, password or admin flag.

    Request: any non-empty subset of `{real_name, password, is_admin}`.
    Response 200: the updated user. Demoting the last administrator is refused.
    """
    payload = json_body(request)
    if not payload:
        raise validation_error(NO_FIELDS_MESSAGE)
    if set(payload) - EDITABLE_USER_FIELDS:
        raise validation_error(UNKNOWN_FIELDS_MESSAGE)

    target = get_active_user(db.session, user_id)
    raw_password = optional_string(
        payload, "password", max_length=MAX_PASSWORD_LENGTH, strip=False
    )
    updated = update_user(
        db.session,
        target=target,
        real_name=optional_string(
            payload, "real_name", max_length=REAL_NAME_MAX_LENGTH
        ),
        password=None if raw_password is None else validate_password(raw_password),
        is_admin=nullable_bool(payload, "is_admin"),
    )
    db.session.commit()
    return respond(serialize_user(updated))


@users_bp.delete("/settings/users/<int:user_id>")
@admin_required
def remove_user(user_id: int) -> Any:
    """Soft-delete a user and invalidate their sessions.

    Response 200: `data: null`. The row is kept so historical records still
    resolve a username, rendered by the frontend with a "(deleted)" tag.
    """
    actor = authenticated_user()
    soft_delete_user(
        db.session, actor=actor, target=get_active_user(db.session, user_id)
    )
    db.session.commit()
    return respond()
