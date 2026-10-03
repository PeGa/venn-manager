"""Table definitions and the imperative mapping of domain entities (BACKEND.md § 2).

Importing this module maps every entity once. Repositories query through the
`Table` columns below, so the domain classes stay plain dataclasses.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Uuid,
)
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.orm import registry
from sqlalchemy.types import TypeDecorator

from app.domain.entities import (
    Activity,
    Budget,
    Household,
    LoginSession,
    Member,
    Transaction,
)


class UTCDateTime(TypeDecorator[datetime]):
    """Store instants as naive UTC; read them back as aware UTC.

    SQLite keeps no time zone, so the zone is normalised on the way in and
    reattached on the way out. Every engine sees the same values.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is None:
            return None
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


metadata = MetaData()

household = Table(
    "household",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("name", String(60), nullable=False),
    Column("currency_sign", String(8), nullable=False),
    Column("timezone", String(64), nullable=False),
    Column("opening_balance", BigInteger, nullable=False),
    Column("show_member_income", Boolean, nullable=False),
    Column("rev", Integer, nullable=False),
)

users = Table(
    "users",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("username", String(64), nullable=False, unique=True),
    Column("real_name", String(128), nullable=False),
    Column("password_hash", String(255), nullable=False),
    Column("must_change_password", Boolean, nullable=False),
    Column("is_admin", Boolean, nullable=False),
    Column("language", String(2), nullable=True),
    Column("theme", String(6), nullable=False),
    Column("color", String(7), nullable=False),
    Column("is_removed", Boolean, nullable=False),
    Column("created_at", UTCDateTime, nullable=False),
)

sessions = Table(
    "sessions",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("token_hash", String(64), nullable=False, unique=True, index=True),
    Column("user_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("created_at", UTCDateTime, nullable=False),
)

budgets = Table(
    "budgets",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("name", String(60), nullable=False, index=True),
    Column("amount", BigInteger, nullable=False),
    Column("schedule_repeat", String(8), nullable=True),
    Column("schedule_anchor", Date, nullable=True),
    Column("is_goal", Boolean, nullable=False),
    Column("is_deleted", Boolean, nullable=False),
    Column("created_by", Uuid, ForeignKey("users.id"), nullable=True),
    Column("created_at", UTCDateTime, nullable=False),
)

transactions = Table(
    "transactions",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("payee", String(120), nullable=False),
    Column("budget_id", Uuid, ForeignKey("budgets.id"), nullable=False, index=True),
    Column("amount", BigInteger, nullable=False),
    Column("member_id", Uuid, ForeignKey("users.id"), nullable=False, index=True),
    Column("date", Date, nullable=False, index=True),
    Column("created_by", Uuid, ForeignKey("users.id"), nullable=False),
    Column("created_at", UTCDateTime, nullable=False),
    Column("updated_at", UTCDateTime, nullable=False),
    Column("is_deleted", Boolean, nullable=False),
)

activity = Table(
    "activity",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("actor_id", Uuid, ForeignKey("users.id"), nullable=False),
    Column("action", String(32), nullable=False),
    Column("params", JSON, nullable=False),
    Column("target_type", String(16), nullable=False),
    Column("target_id", Uuid, nullable=True),
    Column("target_section", String(16), nullable=True),
    Column("at", UTCDateTime, nullable=False, index=True),
)

mapper_registry = registry(metadata=metadata)
mapper_registry.map_imperatively(Household, household)
mapper_registry.map_imperatively(Member, users)
mapper_registry.map_imperatively(LoginSession, sessions)
mapper_registry.map_imperatively(Budget, budgets)
mapper_registry.map_imperatively(Transaction, transactions)
mapper_registry.map_imperatively(Activity, activity)
