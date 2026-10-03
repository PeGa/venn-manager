"""Fixtures: an in-memory database, a frozen clock and a seeded app."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from argon2 import PasswordHasher
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.adapters.persistence.repositories import SqlUnitOfWork, make_engine
from app.adapters.persistence.tables import metadata
from app.adapters.security import Argon2Hasher
from app.application.seed import seed
from app.config import Settings
from app.main import create_app
from tests.helpers import FakeClock

START = datetime(2026, 9, 28, 10, 0, tzinfo=UTC)


@pytest.fixture
def hasher() -> Argon2Hasher:
    """Argon2id with a tiny work factor. Same algorithm and format, far faster."""
    return Argon2Hasher(PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(START)


@pytest.fixture
def settings() -> Settings:
    return Settings(database_url="sqlite://")


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = make_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    with Session(engine, expire_on_commit=False) as session:
        yield session


def seed_database(
    engine: Engine, settings: Settings, hasher: Argon2Hasher, clock: FakeClock
) -> None:
    with Session(engine) as session:
        seed(
            SqlUnitOfWork(session),
            hasher,
            admin_username=settings.default_admin_username,
            admin_password=settings.default_admin_password,
            timezone=settings.default_timezone,
            now=clock.now(),
        )
        session.commit()


@pytest.fixture
def app(
    settings: Settings, engine: Engine, clock: FakeClock, hasher: Argon2Hasher
) -> FastAPI:
    seed_database(engine, settings, hasher, clock)
    return create_app(settings, engine=engine, clock=clock, hasher=hasher)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
