"""Every interface the application layer depends on (AGENTS.md § Hexagonal).

Adapters implement these. Use cases receive them through `Context`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from app.domain.entities import Household, LoginSession, Member


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

    def by_username(self, username: str) -> Member | None:
        """The member with *username*, removed or not."""
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


class TransactionRepository(Protocol):
    """Transactions and their aggregates."""

    def spent_by_member(self, start: date, end: date) -> dict[UUID, int]:
        """Counted money out per member between *start* and *end*, positive."""
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
    def transactions(self) -> TransactionRepository: ...

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
