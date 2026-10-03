"""General and profile settings — API_SURFACE.md § 3.1.

| Method | Route      | Auth | Purpose                                     |
|--------|------------|------|---------------------------------------------|
| GET    | /settings  | yes  | Global settings merged with the user's own  |
| PATCH  | /settings  | yes  | Update settings; scope is chosen by the key |

User management (§ 3.2) and concept management (§ 3.3) live in their own
modules but share the `/settings/...` URL prefix.

Errors: 401 `UNAUTHORIZED`, 403 `FORBIDDEN` / `PASSWORD_CHANGE_REQUIRED`,
409 `CONFLICT` (username taken), 422 `VALIDATION_ERROR`.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, request

from app.extensions import db
from app.middleware.auth import authenticated_user, login_required
from app.middleware.requests import json_body, today
from app.middleware.responses import respond
from app.services.settings import serialize, update

settings_bp = Blueprint("settings", __name__)


@settings_bp.get("/settings")
@login_required
def get_settings() -> Any:
    """Return the six documented settings for the calling user.

    Internal rows such as the session epoch are never included.
    """
    user = authenticated_user()
    return respond(serialize(db.session, user, today()))


@settings_bp.patch("/settings")
@login_required
def patch_settings() -> Any:
    """Update one or more settings.

    Request: any subset of `currency`, `language`, `theme`, `username`,
    `real_name`. Response 200: the keys that changed with their new values.
    Every key is validated before anything is written, so one bad key leaves
    the database untouched.
    """
    user = authenticated_user()
    changes = update(db.session, user, json_body(request))
    db.session.commit()
    return respond(changes)
