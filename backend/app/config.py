"""Runtime configuration, read from environment variables (AGENTS.md § Environment)."""

from __future__ import annotations

import os
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

APP_ENVS = ("development", "production")


@dataclass(frozen=True)
class Settings:
    """Every configurable value. Defaults suit local development."""

    database_url: str = "sqlite:///venn_manager.db"
    app_env: str = "development"
    default_admin_username: str = "admin"
    default_admin_password: str = "admin"  # noqa: S105  (documented default)
    default_timezone: str = "UTC"
    frontend_dist: str | None = None

    @property
    def secure_cookies(self) -> bool:
        """Whether the session cookie carries the `Secure` flag."""
        return self.app_env == "production"


def load_dotenv(path: Path, environ: MutableMapping[str, str] = os.environ) -> None:
    """Copy `KEY=VALUE` lines from *path* into *environ*.

    Variables that are already set are left alone, so an exported value always
    wins over the file. Blank lines, comments and malformed lines are skipped.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        environ.setdefault(key.strip(), value.strip().strip("'\""))


def settings_from_env(environ: Mapping[str, str] = os.environ) -> Settings:
    """Build `Settings` from *environ*, rejecting values that cannot work."""
    defaults = Settings()
    app_env = environ.get("APP_ENV", defaults.app_env)
    if app_env not in APP_ENVS:
        raise ValueError(f"APP_ENV must be one of {', '.join(APP_ENVS)}")
    timezone = environ.get("DEFAULT_TIMEZONE", defaults.default_timezone)
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("DEFAULT_TIMEZONE must be a valid IANA time zone") from exc
    return Settings(
        database_url=environ.get("DATABASE_URL", defaults.database_url),
        app_env=app_env,
        default_admin_username=environ.get(
            "DEFAULT_ADMIN_USERNAME", defaults.default_admin_username
        ),
        default_admin_password=environ.get(
            "DEFAULT_ADMIN_PASSWORD", defaults.default_admin_password
        ),
        default_timezone=timezone,
        frontend_dist=environ.get("FRONTEND_DIST") or None,
    )
