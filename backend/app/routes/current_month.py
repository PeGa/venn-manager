"""Current-month endpoints — API_SURFACE.md § 2.

| Method | Route                   | Auth | Purpose                              |
|--------|-------------------------|------|--------------------------------------|
| GET    | /current-month          | yes  | Report month state and `needs_switch`|
| POST   | /current-month/switch   | yes  | Acknowledge the month change         |

Errors: 401 `UNAUTHORIZED`, 403 `PASSWORD_CHANGE_REQUIRED`, 409 `CONFLICT`
(switch when already on the current month).
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint

from app.extensions import db
from app.middleware.auth import authenticated_user, login_required
from app.middleware.requests import today
from app.middleware.responses import respond
from app.services.months import acknowledge_month, month_state

current_month_bp = Blueprint("current_month", __name__)


@current_month_bp.get("/current-month")
@login_required
def get_current_month() -> Any:
    """Return the server month, the user's working month and whether they differ.

    Response 200: `{current_month, last_acknowledged_month, needs_switch,
    earliest_month}`. `earliest_month` is null when no transaction exists.
    """
    user = authenticated_user()
    return respond(month_state(db.session, user_id=user.id, today=today()))


@current_month_bp.post("/current-month/switch")
@login_required
def switch_month() -> Any:
    """Acknowledge the month change for the calling user only.

    No record is created, moved or modified (BACKEND.md § 3.2).
    Response 200: the same payload as `GET /current-month`, with `needs_switch`
    now false. Errors: 409 `CONFLICT` when there is nothing to switch.
    """
    user = authenticated_user()
    state = acknowledge_month(db.session, user_id=user.id, today=today())
    db.session.commit()
    return respond(state)
