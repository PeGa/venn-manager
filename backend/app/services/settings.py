"""Settings resolution and updates (API_SURFACE.md § 3.1).

Resolution order for a scoped key: the user's own row, then the global row,
then the built-in default. Writes always land in the scope the key belongs to,
so a user changing `language` never moves the global default.

Profile keys (`username`, `real_name`) are *not* settings rows: they live on the
users table, which is how the Profile screen edits them without a dedicated
endpoint.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select

from app.extensions import DbSession
from app.models import Setting, User
from app.models.user import REAL_NAME_MAX_LENGTH, USERNAME_MAX_LENGTH
from app.services.errors import conflict, forbidden, validation_error
from app.services.sessions import SESSION_EPOCH_KEY
from app.utils.dates import month_key
from app.utils.validation import (
    validate_choice,
    validate_currency,
    validate_text,
)

GLOBAL_SCOPE = "global"
USER_SCOPE = "per-user"

CURRENCY = "currency"
LANGUAGE = "language"
THEME = "theme"
LAST_ACKNOWLEDGED_MONTH = "last_acknowledged_month"

LANGUAGES = ("en", "es")
THEMES = ("light", "dark", "system")

USERNAME = "username"
REAL_NAME = "real_name"
PROFILE_SETTINGS = frozenset({USERNAME, REAL_NAME})

#: Never surfaced by GET and never accepted by PATCH.
INTERNAL_SETTINGS = frozenset({SESSION_EPOCH_KEY})

DEFAULTS: dict[str, str] = {
    CURRENCY: "$",
    LANGUAGE: "en",
    THEME: "system",
}


@dataclass(frozen=True)
class SettingSpec:
    """Scope and access rules for one settings key."""

    scope: str
    requires_admin: bool = False
    #: False for keys the contract routes through another endpoint, e.g. the
    #: working month, which only POST /current-month/switch may move.
    writable: bool = True


SETTING_SPECS: dict[str, SettingSpec] = {
    CURRENCY: SettingSpec(GLOBAL_SCOPE),
    LANGUAGE: SettingSpec(USER_SCOPE),
    THEME: SettingSpec(USER_SCOPE),
    LAST_ACKNOWLEDGED_MONTH: SettingSpec(USER_SCOPE, writable=False),
}


def read_raw(session: DbSession, key: str, user_id: int | None) -> str | None:
    """Return the stored value for *key*, preferring the user's own row."""
    if user_id is not None:
        own = session.scalar(
            select(Setting.value).where(Setting.key == key, Setting.user_id == user_id)
        )
        if own is not None:
            return own
    return session.scalar(
        select(Setting.value).where(Setting.key == key, Setting.user_id.is_(None))
    )


def effective(
    session: DbSession, key: str, user_id: int | None, *, default: str
) -> str:
    """Return the value a user sees for *key*, falling back to *default*."""
    stored = read_raw(session, key, user_id)
    return default if stored is None else stored


def working_month(session: DbSession, user_id: int | None, today: date) -> str:
    """Return the user's working month (BACKEND.md § 1.4).

    A user who has never acknowledged a month works in the current one.
    """
    return effective(
        session, LAST_ACKNOWLEDGED_MONTH, user_id, default=month_key(today)
    )


def write_setting(
    session: DbSession, key: str, value: str, user_id: int | None
) -> None:
    """Upsert *key* into the scope its spec declares. Flushes; caller commits."""
    spec = SETTING_SPECS[key]
    owner = None if spec.scope == GLOBAL_SCOPE else user_id
    condition = Setting.user_id.is_(None) if owner is None else Setting.user_id == owner
    row = session.scalar(select(Setting).where(Setting.key == key, condition))
    if row is None:
        session.add(
            Setting(
                key=key,
                value=value,
                user_id=owner,
                requires_admin=spec.requires_admin,
            )
        )
    else:
        row.value = value
    session.flush()


def serialize(session: DbSession, user: User, today: date) -> dict[str, Any]:
    """Build the `GET /settings` payload: global merged with per-user values."""
    return {
        CURRENCY: effective(session, CURRENCY, user.id, default=DEFAULTS[CURRENCY]),
        LANGUAGE: effective(session, LANGUAGE, user.id, default=DEFAULTS[LANGUAGE]),
        THEME: effective(session, THEME, user.id, default=DEFAULTS[THEME]),
        LAST_ACKNOWLEDGED_MONTH: working_month(session, user.id, today),
        USERNAME: user.username,
        REAL_NAME: user.real_name,
    }


def update(
    session: DbSession, user: User, payload: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate every submitted key, then apply them. Returns the new values.

    Validation completes before any write, so a payload with one bad key leaves
    the database untouched.
    """
    if not payload:
        raise validation_error("At least one setting must be provided")
    validated = {
        key: _validate(session, user, key, value) for key, value in payload.items()
    }
    _apply(session, user, validated)
    return validated


def _validate(session: DbSession, user: User, key: str, value: Any) -> str:
    """Return the cleaned value for *key*, or raise a contract error.

    The unknown-key message is deliberately generic: AGENTS.md § XSS Prevention
    forbids reflecting unvalidated request input. The read-only message may name
    the key because it is one of our own constants.
    """
    if key in PROFILE_SETTINGS:
        return _validate_profile(session, user, key, value)
    spec = SETTING_SPECS.get(key)
    if spec is None:
        raise validation_error("Unknown setting key")
    if not spec.writable:
        raise validation_error(f"Setting '{key}' is read-only")
    if spec.requires_admin and not user.is_admin:
        raise forbidden("Administrator role required")
    return _validate_value(key, value)


def _validate_value(key: str, value: Any) -> str:
    if key == CURRENCY:
        return validate_currency(value)
    if key == LANGUAGE:
        return validate_choice(value, key, LANGUAGES)
    return validate_choice(value, key, THEMES)


def _validate_profile(session: DbSession, user: User, key: str, value: Any) -> str:
    if key == USERNAME:
        username = validate_text(value, field=key, max_length=USERNAME_MAX_LENGTH)
        if username != user.username and _username_taken(session, username):
            raise conflict("Username already taken")
        return username
    return validate_text(value, field=key, max_length=REAL_NAME_MAX_LENGTH)


def _username_taken(session: DbSession, username: str) -> bool:
    """True when any row holds *username*, including soft-deleted ones.

    API_SURFACE.md § User Soft-Delete: a deleted user's username stays reserved.
    """
    return session.scalar(select(User.id).where(User.username == username)) is not None


def _apply(session: DbSession, user: User, validated: Mapping[str, str]) -> None:
    for key, value in validated.items():
        if key == USERNAME:
            user.username = value
        elif key == REAL_NAME:
            user.real_name = value
        else:
            write_setting(session, key, value, user.id)
    session.flush()
