"""Test-only helpers shared across suites."""

from __future__ import annotations

from typing import Any

from flask import Flask

from app.middleware.auth import admin_required, authenticated_user, login_required
from app.middleware.responses import respond


def register_probe_routes(app: Flask) -> None:
    """Mount throwaway routes that exercise the auth decorators.

    The contract defines no such endpoints; they exist so the gate can be
    tested before (and independently of) the real route modules.
    """

    @app.route("/api/v1/_probe")
    @login_required
    def _probe() -> Any:
        user = authenticated_user()
        return respond({"username": user.username, "user_id": user.id})

    @app.route("/api/v1/_admin")
    @admin_required
    def _admin() -> Any:
        return respond({"ok": True})
