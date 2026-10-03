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

from app.adapters.persistence.tables import (
    activity,
    budgets,
    sessions,
    transactions,
    users,
)
from app.domain.entities import (
    Activity,
    Budget,
    Household,
    LoginSession,
    Member,
    Transaction,
)


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

    def get(self, member_id: UUID) -> Member | None:
        return self.db.get(Member, member_id)

    def all(self) -> list[Member]:
        return list(self.db.scalars(select(Member).order_by(users.c.created_at)))

    def active_admin_count(self) -> int:
        count = self.db.scalar(
            select(func.count())
            .select_from(users)
            .where(users.c.is_admin.is_(True), users.c.is_removed.is_(False))
        )
        return int(count or 0)

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


class SqlBudgets:
    """`BudgetRepository` over the `budgets` table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, budget_id: UUID) -> Budget | None:
        return self.db.get(Budget, budget_id)

    def active(self) -> list[Budget]:
        return list(
            self.db.scalars(
                select(Budget)
                .where(budgets.c.is_deleted.is_(False))
                .order_by(budgets.c.created_at)
            )
        )

    def name_taken(self, name: str, except_id: UUID | None = None) -> bool:
        statement = select(budgets.c.id).where(
            budgets.c.is_deleted.is_(False),
            func.lower(budgets.c.name) == name.lower(),
        )
        if except_id is not None:
            statement = statement.where(budgets.c.id != except_id)
        return self.db.scalar(statement.limit(1)) is not None

    def add(self, budget: Budget) -> None:
        self.db.add(budget)


class SqlTransactions:
    """`TransactionRepository` over the `transactions` table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, transaction_id: UUID) -> tuple[Transaction, Budget] | None:
        row = self.db.execute(
            select(Transaction, Budget)
            .join(budgets, budgets.c.id == transactions.c.budget_id)
            .where(transactions.c.id == transaction_id)
        ).first()
        return None if row is None else (row[0], row[1])

    def add(self, transaction: Transaction) -> None:
        self.db.add(transaction)

    def page(
        self, start: date, end: date, offset: int, limit: int
    ) -> list[tuple[Transaction, Budget]]:
        rows = self.db.execute(
            select(Transaction, Budget)
            .join(budgets, budgets.c.id == transactions.c.budget_id)
            .where(
                transactions.c.is_deleted.is_(False),
                transactions.c.date.between(start, end),
            )
            .order_by(transactions.c.date.desc(), transactions.c.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return [(row[0], row[1]) for row in rows]

    def count(self, start: date, end: date) -> int:
        total = self.db.scalar(
            select(func.count())
            .select_from(transactions)
            .where(
                transactions.c.is_deleted.is_(False),
                transactions.c.date.between(start, end),
            )
        )
        return int(total or 0)

    def actual_by_budget(self, start: date, end: date) -> dict[UUID, int]:
        rows = self.db.execute(
            select(transactions.c.budget_id, func.sum(transactions.c.amount))
            .join(budgets, budgets.c.id == transactions.c.budget_id)
            .where(counted(), transactions.c.date.between(start, end))
            .group_by(transactions.c.budget_id)
        ).all()
        return {budget_id: int(total) for budget_id, total in rows}

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


class SqlActivity:
    """`ActivityRepository` over the `activity` table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, entry: Activity) -> None:
        self.db.add(entry)

    def newest(self) -> Activity | None:
        return self.db.scalars(
            select(Activity).order_by(activity.c.at.desc()).limit(1)
        ).first()


class SqlUnitOfWork:
    """`UnitOfWork` sharing one SQLAlchemy session across repositories."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.household = SqlHouseholds(db)
        self.members = SqlMembers(db)
        self.sessions = SqlSessions(db)
        self.budgets = SqlBudgets(db)
        self.transactions = SqlTransactions(db)
        self.activity = SqlActivity(db)

    def commit(self) -> None:
        self.db.commit()
