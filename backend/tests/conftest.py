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

from app.auth import passwords
from app.config import Settings
from app.db import Base, make_engine
from app.main import create_app
from app.services.seed import seed
from tests.helpers import FakeClock

START = datetime(2026, 9, 28, 10, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def cheap_hashing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Argon2id with a tiny work factor. Same algorithm and format, far faster."""
    monkeypatch.setattr(
        passwords, "hasher", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)
    )


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
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    with Session(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def app(settings: Settings, engine: Engine, clock: FakeClock) -> FastAPI:
    with Session(engine) as session:
        seed(session, settings, clock.now())
        session.commit()
    return create_app(settings, engine=engine, clock=clock)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
