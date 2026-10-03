"""Every interface the application layer depends on (AGENTS.md § Hexagonal).

Adapters implement these. Use cases receive them through `Context`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from app.domain.entities import (
    Activity,
    Budget,
    Household,
    LoginSession,
    Member,
    Transaction,
)
from app.domain.history import HistoryFilter


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

    def used_before(self, day: date) -> list[Member]:
        """Members with a non-deleted transaction before *day*, creation order."""
        ...

    def get_many(self, member_ids: set[UUID]) -> dict[UUID, Member]:
        """Members by id, removed ones included. Unknown ids are absent."""
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

    def used_before(self, day: date) -> list[Budget]:
        """Budgets with a non-deleted transaction before *day*, creation order."""
        ...

    def get_many(self, budget_ids: set[UUID]) -> dict[UUID, Budget]:
        """Budgets by id, deleted ones included. Unknown ids are absent."""
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

    def get(self, transaction_id: UUID) -> tuple[Transaction, Budget] | None:
        """The transaction with *transaction_id* and its budget, deleted or not."""
        ...

    def get_many(self, transaction_ids: set[UUID]) -> dict[UUID, Transaction]:
        """Transactions by id, deleted ones included. Unknown ids are absent."""
        ...

    def add(self, transaction: Transaction) -> None:
        """Store a new transaction."""
        ...

    def net_before(self, day: date) -> int:
        """Signed sum of counted transactions dated before *day*."""
        ...

    def counted_between(self, start: date, end: date) -> int:
        """How many counted transactions fall between the dates."""
        ...

    def flows(self, start: date, end: date) -> tuple[int, int]:
        """Counted money in and money out between the dates, both positive."""
        ...

    def income_by_member(
        self, start: date | None = None, end: date | None = None
    ) -> dict[UUID, int]:
        """Counted positive amounts per member, optionally between the dates."""
        ...

    def page(
        self,
        start: date,
        end: date,
        offset: int,
        limit: int,
        filters: HistoryFilter | None = None,
    ) -> list[tuple[Transaction, Budget]]:
        """Non-deleted transactions between the dates with their budgets.

        Newest first: date descending, then creation descending.
        """
        ...

    def count(
        self, start: date, end: date, filters: HistoryFilter | None = None
    ) -> int:
        """How many non-deleted transactions fall between the dates."""
        ...

    def months_before(
        self,
        day: date,
        filters: HistoryFilter | None = None,
        since: date | None = None,
    ) -> list[tuple[int, int, int, int, int]]:
        """Per month before *day* (and from *since*), newest first.

        Each row is (year, month, rows, spent, earned).

        Rows count every matching non-deleted transaction; spent and earned
        only counted ones, both positive.
        """
        ...

    def spending_by_budget(
        self, start: date, end: date, filters: HistoryFilter | None = None
    ) -> list[tuple[UUID, str, int]]:
        """Counted money out per budget between the dates, largest first."""
        ...

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

    def page(self, offset: int, limit: int) -> list[Activity]:
        """Entries newest first."""
        ...

    def count(self) -> int:
        """How many entries exist."""
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
