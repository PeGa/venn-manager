"""Application factory for Venn Manager's backend API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask import Flask

from app.config import build_config
from app.extensions import db, migrate
from app.middleware.auth import init_auth
from app.middleware.errors import register_error_handlers
from app.routes import register_blueprints
from app.utils.json import ContractJSONProvider


def create_app(overrides: Mapping[str, Any] | None = None) -> Flask:
    """Build and configure the Flask application.

    *overrides* wins over the environment, which is how tests inject a private
    database, a test secret key and a frozen clock.
    """
    # Imported for its side effect: registering every table on the metadata so
    # `flask db migrate` and `db.create_all()` can see them. Kept function-local
    # to avoid a cycle between the package root and app.models.
    from app import models  # noqa: F401

    application = Flask(__name__)
    application.config.update(build_config(overrides))
    # Contract-exact wire format: two-decimal JSON numbers, Zulu timestamps.
    application.json = ContractJSONProvider(application)

    db.init_app(application)
    migrate.init_app(application, db)
    init_auth(application)

    register_error_handlers(application)
    register_blueprints(application)
    return application
