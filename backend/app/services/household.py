"""Access to the single household row and its revision (BACKEND.md § 1, § 10)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Household
from app.services.period import Period, current_period


def get_household(db: Session) -> Household:
    """The household. Seeding guarantees it exists."""
    return db.scalars(select(Household)).one()


def period_for(db: Session, now: datetime) -> Period:
    """The current period in the household's time zone."""
    return current_period(get_household(db).timezone, now)


def commit_mutation(db: Session) -> None:
    """Bump the revision and commit, in the same transaction as the change."""
    get_household(db).rev += 1
    db.commit()
