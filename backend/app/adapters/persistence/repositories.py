"""SQLAlchemy implementations of the repository ports (`app/ports.py`)."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    Engine,
    and_,
    create_engine,
    delete,
    event,
    func,
    select,
)
from sqlalchemy.orm import Session

from app.adapters.persistence.tables import budgets, sessions, transactions, users
from app.domain.entities import Household, LoginSession, Member


def make_engine(url: str, **kwargs: Any) -> Engine:
    """Create an engine. SQLite connections enforce foreign keys."""
    engine = create_engine(url, **kwargs)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def counted() -> ColumnElement[bool]:
    """A transaction counts when neither it nor its budget is deleted (§ 4.1).

    Queries using this must join `budgets` on `transactions.budget_id`.
    """
    return and_(transactions.c.is_deleted.is_(False), budgets.c.is_deleted.is_(False))


class SqlHouseholds:
    """`HouseholdRepository` over the `household` table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self) -> Household:
        return self.db.scalars(select(Household)).one()

    def add(self, household: Household) -> None:
        self.db.add(household)

    def exists(self) -> bool:
        return self.db.scalar(select(Household).limit(1)) is not None


class SqlMembers:
    """`MemberRepository` over the `users` table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def by_username(self, username: str) -> Member | None:
        return self.db.scalars(
            select(Member).where(users.c.username == username)
        ).first()

    def add(self, member: Member) -> None:
        self.db.add(member)


class SqlSessions:
    """`SessionRepository` over the `sessions` table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, session: LoginSession) -> None:
        self.db.add(session)

    def find(self, token_hash: str) -> tuple[LoginSession, Member] | None:
        row = self.db.execute(
            select(LoginSession, Member)
            .join(users, users.c.id == sessions.c.user_id)
            .where(sessions.c.token_hash == token_hash, users.c.is_removed.is_(False))
        ).first()
        return None if row is None else (row[0], row[1])

    def delete(self, session: LoginSession) -> None:
        self.db.delete(session)

    def delete_for_member(self, member_id: UUID, keep: UUID | None = None) -> None:
        statement = delete(sessions).where(sessions.c.user_id == member_id)
        if keep is not None:
            statement = statement.where(sessions.c.id != keep)
        self.db.execute(statement)


class SqlTransactions:
    """`TransactionRepository` over the `transactions` table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def spent_by_member(self, start: date, end: date) -> dict[UUID, int]:
        rows = self.db.execute(
            select(transactions.c.member_id, func.sum(-transactions.c.amount))
            .join(budgets, budgets.c.id == transactions.c.budget_id)
            .where(
                counted(),
                transactions.c.amount < 0,
                transactions.c.date.between(start, end),
            )
            .group_by(transactions.c.member_id)
        ).all()
        return {member_id: int(total) for member_id, total in rows}


class SqlUnitOfWork:
    """`UnitOfWork` sharing one SQLAlchemy session across repositories."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.household = SqlHouseholds(db)
        self.members = SqlMembers(db)
        self.sessions = SqlSessions(db)
        self.transactions = SqlTransactions(db)

    def commit(self) -> None:
        self.db.commit()
