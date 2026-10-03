"""Projections — API_SURFACE.md § 5.

| Method | Route         | Auth | Purpose                              |
|--------|---------------|------|--------------------------------------|
| GET    | /projections  | yes  | Computed projections for one month   |

Read-only and computed per request; nothing is stored or cached.
Errors: 401 `UNAUTHORIZED`, 403 `PASSWORD_CHANGE_REQUIRED`,
422 `VALIDATION_ERROR` (missing or malformed `month`).
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, request

from app.extensions import db
from app.middleware.auth import authenticated_user, login_required
from app.middleware.requests import require_query, today
from app.middleware.responses import respond
from app.services.projections import month_projections
from app.services.settings import working_month
from app.utils.validation import parse_month

projections_bp = Blueprint("projections", __name__)


@projections_bp.get("/projections")
@login_required
def index() -> Any:
    """Return the five projection figures for one month.

    Query: `month` (required, `YYYY-MM`). Response 200: `{spend_projection,
    earn_projection, savings_projection, actual_spend, actual_earn}`.

    Whether a deleted concept's transactions count depends on the *requesting
    user's* working month, so two users can legitimately see different figures
    for the same month until both acknowledge the switch (BACKEND.md § 1.2).
    """
    user = authenticated_user()
    month = parse_month(require_query(request, "month"))
    result = month_projections(
        db.session,
        month=month,
        working_month=working_month(db.session, user.id, today()),
    )
    return respond(result)
