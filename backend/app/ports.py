"""Every interface the application layer depends on (AGENTS.md § Hexagonal).

Adapters implement these. Use cases receive them through `Context`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from app.domain.entities import Activity, Budget, Household, LoginSession, Member


class Clock(Protocol):
    """The source of "now"."""

    def now(self) -> datetime:
        """The current instant, aware, in UTC."""
        ...


class PasswordHasher(Protocol):
    """One-way password hashing."""

    def hash(self, password: str) -> str:
        """An encoded hash of *password*."""
        ...

    def verify(self, password_hash: str, password: str) -> bool:
        """Whether *password* matches *password_hash*."""
        ...


class TokenGenerator(Protocol):
    """Session tokens and their stored digests."""

    def new_token(self) -> str:
        """A fresh unguessable token for the cookie."""
        ...

    def digest(self, token: str) -> str:
        """What the database stores instead of *token*."""
        ...


class HouseholdRepository(Protocol):
    """The single household row."""

    def get(self) -> Household:
        """The household. Seeding guarantees it exists."""
        ...

    def add(self, household: Household) -> None:
        """Store the household (seeding only)."""
        ...

    def exists(self) -> bool:
        """Whether the household was seeded."""
        ...


class MemberRepository(Protocol):
    """Members, removed ones included."""

    def get(self, member_id: UUID) -> Member | None:
        """The member with *member_id*, removed or not."""
        ...

    def by_username(self, username: str) -> Member | None:
        """The member with *username*, removed or not."""
        ...

    def all(self) -> list[Member]:
        """Every member, removed ones included, in creation order."""
        ...

    def active_admin_count(self) -> int:
        """How many active members are admins."""
        ...

    def add(self, member: Member) -> None:
        """Store a new member."""
        ...


class SessionRepository(Protocol):
    """Server-side sessions."""

    def add(self, session: LoginSession) -> None:
        """Store a new session."""
        ...

    def find(self, token_hash: str) -> tuple[LoginSession, Member] | None:
        """The session with *token_hash* and its member, if the member is active."""
        ...

    def delete(self, session: LoginSession) -> None:
        """Remove one session."""
        ...

    def delete_for_member(self, member_id: UUID, keep: UUID | None = None) -> None:
        """Remove every session of *member_id* except *keep*."""
        ...


class BudgetRepository(Protocol):
    """Budgets (concepts), deleted ones included."""

    def get(self, budget_id: UUID) -> Budget | None:
        """The budget with *budget_id*, deleted or not."""
        ...

    def active(self) -> list[Budget]:
        """Non-deleted budgets in creation order."""
        ...

    def name_taken(self, name: str, except_id: UUID | None = None) -> bool:
        """Whether a non-deleted budget other than *except_id* uses *name*.

        The comparison ignores case.
        """
        ...

    def add(self, budget: Budget) -> None:
        """Store a new budget."""
        ...


class TransactionRepository(Protocol):
    """Transactions and their aggregates."""

    def actual_by_budget(self, start: date, end: date) -> dict[UUID, int]:
        """Signed sum of counted transactions per budget between the dates."""
        ...

    def spent_by_member(self, start: date, end: date) -> dict[UUID, int]:
        """Counted money out per member between *start* and *end*, positive."""
        ...


class ActivityRepository(Protocol):
    """The activity feed."""

    def add(self, entry: Activity) -> None:
        """Store a new entry."""
        ...

    def newest(self) -> Activity | None:
        """The most recent entry, if any."""
        ...


class UnitOfWork(Protocol):
    """Repositories sharing one database transaction."""

    @property
    def household(self) -> HouseholdRepository: ...

    @property
    def members(self) -> MemberRepository: ...

    @property
    def sessions(self) -> SessionRepository: ...

    @property
    def budgets(self) -> BudgetRepository: ...

    @property
    def transactions(self) -> TransactionRepository: ...

    @property
    def activity(self) -> ActivityRepository: ...

    def commit(self) -> None:
        """Make every change since the last commit permanent."""
        ...


@dataclass(frozen=True)
class Context:
    """Everything a use case may touch."""

    uow: UnitOfWork
    clock: Clock
    hasher: PasswordHasher
    tokens: TokenGenerator
