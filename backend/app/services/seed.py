"""Seeding (CONTRACTS/BACKEND.md § 4).

Runs from the initial migration so a fresh install can log in immediately.
The function flushes but never commits: Alembic owns the surrounding
transaction, and committing here would close it early.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.extensions import DbSession
from app.models import Setting, User
from app.utils.dates import month_key

#: Global settings written on first run (BACKEND.md § 4.2). Concepts are
#: deliberately absent: the app starts empty (§ 4.3).
GLOBAL_DEFAULTS: dict[str, str] = {
    "currency": "$",
    "language": "en",
    "theme": "system",
}

ADMIN_REAL_NAME = "Administrator"


def seed_initial_data(
    session: DbSession,
    *,
    admin_username: str,
    admin_password: str,
    today: date,
) -> bool:
    """Create the first-run baseline state. Returns False if already seeded.

    The user count is the idempotency guard, so re-running the migration on a
    populated database is a no-op rather than a duplicate-key failure.
    """
    if session.scalar(select(User.id).limit(1)) is not None:
        return False

    session.add(
        User.create(
            username=admin_username,
            password=admin_password,
            real_name=ADMIN_REAL_NAME,
            is_admin=True,
        )
    )
    settings = [
        Setting(key=key, value=value, user_id=None, requires_admin=False)
        for key, value in GLOBAL_DEFAULTS.items()
    ]
    # The working month starts at the month the migration ran in (§ 4.2).
    settings.append(
        Setting(
            key="last_acknowledged_month",
            value=month_key(today),
            user_id=None,
            requires_admin=False,
        )
    )
    session.add_all(settings)
    session.flush()
    return True
