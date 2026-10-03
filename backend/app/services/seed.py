"""First-run data (BACKEND.md § 11). Called by the initial migration."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.passwords import hash_password
from app.config import Settings
from app.models import Household, User
from app.models.user import AVATAR_COLORS

SEED_HOUSEHOLD_NAME = "Hogar"
SEED_ADMIN_REAL_NAME = "Administrador"


def seed(db: Session, settings: Settings, now: datetime) -> None:
    """Create the household and the first admin, unless they already exist."""
    if db.scalar(select(Household.id).limit(1)) is not None:
        return
    db.add(
        Household(
            name=SEED_HOUSEHOLD_NAME,
            currency_sign="$",
            timezone=settings.default_timezone,
            opening_balance=0,
            show_member_income=False,
            rev=1,
        )
    )
    db.add(
        User(
            username=settings.default_admin_username,
            real_name=SEED_ADMIN_REAL_NAME,
            password_hash=hash_password(settings.default_admin_password),
            must_change_password=True,
            is_admin=True,
            language=None,
            theme="system",
            color=AVATAR_COLORS[0],
            is_removed=False,
            created_at=now,
        )
    )
