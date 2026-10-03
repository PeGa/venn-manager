"""First-run data (BACKEND.md § 11). Called by the initial migration."""

from __future__ import annotations

from datetime import datetime

from app.domain.entities import Household, Member
from app.domain.members import avatar_color
from app.ports import PasswordHasher, UnitOfWork

SEED_HOUSEHOLD_NAME = "Hogar"
SEED_ADMIN_REAL_NAME = "Administrador"


def seed(
    uow: UnitOfWork,
    hasher: PasswordHasher,
    *,
    admin_username: str,
    admin_password: str,
    timezone: str,
    now: datetime,
) -> None:
    """Create the household and the first admin, unless already seeded."""
    if uow.household.exists():
        return
    uow.household.add(
        Household(name=SEED_HOUSEHOLD_NAME, currency_sign="$", timezone=timezone)
    )
    uow.members.add(
        Member(
            username=admin_username,
            real_name=SEED_ADMIN_REAL_NAME,
            password_hash=hasher.hash(admin_password),
            is_admin=True,
            color=avatar_color(0),
            created_at=now,
        )
    )
