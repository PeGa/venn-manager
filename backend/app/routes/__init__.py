"""Blueprint registration.

One blueprint per contract section (API_SURFACE.md § Endpoint Summary). All are
mounted under `/api/v1`, so no route function repeats the prefix.
"""

from __future__ import annotations

from flask import Blueprint, Flask

from app.routes.auth import auth_bp
from app.routes.concepts import concepts_bp
from app.routes.current_month import current_month_bp
from app.routes.projections import projections_bp
from app.routes.records import records_bp
from app.routes.settings import settings_bp
from app.routes.users import users_bp

API_PREFIX = "/api/v1"

BLUEPRINTS: tuple[Blueprint, ...] = (
    auth_bp,
    current_month_bp,
    settings_bp,
    users_bp,
    concepts_bp,
    records_bp,
    projections_bp,
)


def register_blueprints(app: Flask) -> None:
    """Mount every API blueprint on *app* under the versioned prefix."""
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint, url_prefix=API_PREFIX)
