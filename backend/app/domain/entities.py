"""Domain entities (BACKEND.md § 2).

Plain dataclasses. The persistence adapter maps them to tables imperatively,
so a new field is added here, in its table and in a migration — nowhere else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(eq=False)
class Household:
    """Shared settings plus the ledger revision (BACKEND.md § 1, § 10)."""

    name: str
    currency_sign: str
    timezone: str
    opening_balance: int = 0
    show_member_income: bool = False
    rev: int = 1
    id: UUID = field(default_factory=uuid4)


@dataclass(eq=False)
class Member:
    """A household member and their credentials (BACKEND.md § 8)."""

    username: str
    real_name: str
    password_hash: str
    is_admin: bool
    color: str
    created_at: datetime
    must_change_password: bool = True
    language: str | None = None
    theme: str = "system"
    is_removed: bool = False
    id: UUID = field(default_factory=uuid4)


@dataclass(eq=False)
class LoginSession:
    """One signed-in browser. Only a digest of the cookie token is kept."""

    token_hash: str
    user_id: UUID
    created_at: datetime
    id: UUID = field(default_factory=uuid4)


@dataclass(eq=False)
class Budget:
    """A concept (its name) and its budget (BACKEND.md § 6)."""

    name: str
    created_at: datetime
    created_by: UUID | None = None
    amount: int = 0
    schedule_repeat: str | None = None
    schedule_anchor: date | None = None
    is_goal: bool = False
    is_deleted: bool = False
    id: UUID = field(default_factory=uuid4)


@dataclass(eq=False)
class Transaction:
    """A signed movement of money against one budget (BACKEND.md § 7)."""

    budget_id: UUID
    amount: int
    member_id: UUID
    date: date
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    id: UUID = field(default_factory=uuid4)


@dataclass(eq=False)
class Activity:
    """An informational feed entry (BACKEND.md § 9)."""

    actor_id: UUID
    action: str
    at: datetime
    target_type: str
    params: dict[str, Any] = field(default_factory=dict)
    target_id: UUID | None = None
    target_section: str | None = None
    id: UUID = field(default_factory=uuid4)
