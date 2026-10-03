"""Application configuration.

Every value originates in the environment (AGENTS.md § Environment & Secrets).
`create_app` accepts an override mapping so tests can inject a database URL, a
secret key and a frozen clock without mutating the process environment.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path
from typing import Any

from app.utils.env import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_ROOT / ".env"

#: AGENTS.md § Environment & Secrets: at least 32 bytes, from the environment.
MINIMUM_SECRET_KEY_BYTES = 32

DEFAULT_DATABASE_URL = "sqlite:///venn_manager.db"
PRODUCTION = "production"


Clock = Callable[[], date]
"""Callable returning "today". Injected so month logic stays testable."""


def _load_environment() -> None:
    load_dotenv(ENV_FILE)


def _require_secret_key(value: Any) -> str:
    """Validate SECRET_KEY without ever echoing it into an error or a log."""
    if (
        not isinstance(value, str)
        or len(value.encode("utf-8")) < MINIMUM_SECRET_KEY_BYTES
    ):
        raise RuntimeError(
            "SECRET_KEY must be set in the environment and be at least "
            f"{MINIMUM_SECRET_KEY_BYTES} bytes"
        )
    return value


def build_config(overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Assemble the Flask config from the environment plus *overrides*."""
    _load_environment()
    config: dict[str, Any] = {
        "SECRET_KEY": os.environ.get("SECRET_KEY", ""),
        "SQLALCHEMY_DATABASE_URI": os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "FLASK_ENV": os.environ.get("FLASK_ENV", "development"),
        # Session cookie posture: AGENTS.md § Authentication & Session Security.
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        # Seeding inputs, consumed only by the first migration (BACKEND.md § 4).
        "DEFAULT_ADMIN_USERNAME": os.environ.get("DEFAULT_ADMIN_USERNAME", "admin"),
        "DEFAULT_ADMIN_PASSWORD": os.environ.get("DEFAULT_ADMIN_PASSWORD", "admin"),
        # Test seam: the month logic reads "today" through this callable.
        "CLOCK": date.today,
    }
    if overrides:
        config.update(overrides)
    config.setdefault("SESSION_COOKIE_SECURE", config["FLASK_ENV"] == PRODUCTION)
    config["SECRET_KEY"] = _require_secret_key(config["SECRET_KEY"])
    return config
