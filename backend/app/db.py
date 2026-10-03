"""Database engine, declarative base and the per-request session."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from sqlalchemy import DateTime, Engine, create_engine, event
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    """Declarative base for every model."""


class UTCDateTime(TypeDecorator[datetime]):
    """Store instants as naive UTC; read them back as aware UTC.

    SQLite has no time zone support, so the zone is normalised on the way in
    and reattached on the way out. Every engine sees the same values.
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


def get_db(request: Request) -> Iterator[Session]:
    """Yield one session per request. Routes commit explicitly."""
    with request.app.state.sessionmaker() as session:
        yield session
