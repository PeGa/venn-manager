"""Shared pytest fixtures.

Each test gets its own SQLite file under ``tmp_path`` and its own Flask app, so
no test can observe another's writes and none depends on execution order
(AGENTS.md § Test Structure). The clock is injected rather than read from the
system, which keeps month-sensitive assertions deterministic.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from datetime import date
from decimal import Decimal

import pytest
from flask import Flask, g
from flask.testing import FlaskClient

from app import config as app_config, create_app
from app.extensions import DbSession, db
from app.models import Budget, Concept, Setting, Transaction, User, user as user_model

# A fixed "today" inside July 2025. Tests that need a different working month
# override the seeded `last_acknowledged_month` instead of moving the clock.
FROZEN_TODAY = date(2025, 7, 15)
TEST_SECRET_KEY = "pytest-only-secret-key-not-used-in-production"


@pytest.fixture(autouse=True)
def cheap_password_hashing(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lower the scrypt work factor for the test suite only.

    Production uses werkzeug's default parameters (n=32768, r=8, p=1), which cost
    roughly 34 MB and 0.1 s per hash — enough to dominate a suite that
    authenticates hundreds of times. Only the cost parameter changes: the
    algorithm, salt handling and stored format are identical, and the parameters
    travel inside each hash, so verification still exercises the real code path.
    """
    if request.node.get_closest_marker("production_hashing") is not None:
        return
    monkeypatch.setattr(user_model, "HASH_METHOD", "scrypt:1024:8:1")


def _drop_cached_login_user(_error: BaseException | None) -> None:
    """Drop Flask-Login's per-request user cache.

    Flask binds `g` to the *app* context, and the fixture below keeps one open
    for the whole test, so without this hook a user resolved during one request
    would be reused by the next one. Production pushes a fresh app context per
    request and needs no such hook.
    """
    g.pop("_login_user", None)


@pytest.fixture(autouse=True)
def isolated_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Keep the developer's shell and `backend/.env` out of the test suite.

    `build_config` loads `.env` and then reads the process environment, so
    without this a locally configured SECRET_KEY, DATABASE_URL or FLASK_ENV
    would leak into assertions — a test that expects a missing SECRET_KEY would
    pass on a clean machine and fail on a configured one.
    """
    monkeypatch.setattr(
        app_config, "ENV_FILE", tmp_path_factory.mktemp("env") / "absent.env"
    )
    for variable in (
        "SECRET_KEY",
        "DATABASE_URL",
        "FLASK_ENV",
        "DEFAULT_ADMIN_USERNAME",
        "DEFAULT_ADMIN_PASSWORD",
    ):
        monkeypatch.delenv(variable, raising=False)


@pytest.fixture()
def app(isolated_environment: None, tmp_path: os.PathLike[str]) -> Iterator[Flask]:
    """Build an application with an empty database and a frozen clock."""
    database_path = os.path.join(str(tmp_path), "test.db")
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": TEST_SECRET_KEY,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "CLOCK": lambda: FROZEN_TODAY,
            "DEFAULT_ADMIN_USERNAME": "admin",
            "DEFAULT_ADMIN_PASSWORD": "admin",
        }
    )
    application.teardown_request(_drop_cached_login_user)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """A test client bound to the per-test application."""
    return app.test_client()


@pytest.fixture()
def session(app: Flask) -> Iterator[DbSession]:
    """The scoped SQLAlchemy session, inside an application context."""
    yield db.session


@pytest.fixture()
def make_user(app: Flask) -> Callable[..., User]:
    """Create and persist a user. Password defaults to ``secret-pass``."""

    def _make(
        username: str = "alice",
        *,
        password: str = "secret-pass",
        real_name: str | None = None,
        is_admin: bool = False,
        is_deleted: bool = False,
    ) -> User:
        user = User.create(
            username=username,
            password=password,
            real_name=real_name if real_name is not None else username.title(),
            is_admin=is_admin,
        )
        user.is_deleted = is_deleted
        db.session.add(user)
        db.session.commit()
        return user

    return _make


@pytest.fixture()
def make_concept(app: Flask) -> Callable[..., Concept]:
    """Create and persist a concept owned by ``created_by``."""

    def _make(
        name: str = "Groceries",
        *,
        flow: str = "out",
        created_by: User | None = None,
        is_deleted: bool = False,
    ) -> Concept:
        concept = Concept(
            name=name,
            flow=flow,
            created_by=None if created_by is None else created_by.id,
            is_deleted=is_deleted,
        )
        db.session.add(concept)
        db.session.commit()
        return concept

    return _make


@pytest.fixture()
def make_transaction(app: Flask) -> Callable[..., Transaction]:
    """Create and persist a transaction."""

    def _make(
        *,
        concept: Concept,
        user: User,
        amount: Decimal | str | int,
        on: date,
        is_deleted: bool = False,
    ) -> Transaction:
        transaction = Transaction(
            date=on,
            concept_id=concept.id,
            amount=Decimal(str(amount)),
            user_id=user.id,
            is_deleted=is_deleted,
        )
        db.session.add(transaction)
        db.session.commit()
        return transaction

    return _make


@pytest.fixture()
def make_budget(app: Flask) -> Callable[..., Budget]:
    """Create and persist a budget entry. ``amount`` may be ``None``."""

    def _make(
        *,
        concept: Concept,
        user: User,
        amount: Decimal | str | int | None,
        on: date,
        is_deleted: bool = False,
    ) -> Budget:
        budget = Budget(
            date=on,
            concept_id=concept.id,
            amount=None if amount is None else Decimal(str(amount)),
            user_id=user.id,
            is_deleted=is_deleted,
        )
        db.session.add(budget)
        db.session.commit()
        return budget

    return _make


@pytest.fixture()
def login(client: FlaskClient) -> Callable[..., None]:
    """Authenticate the test client as an existing user."""

    def _login(username: str = "alice", password: str = "secret-pass") -> None:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200, response.get_json()

    return _login


@pytest.fixture()
def put_setting(app: Flask) -> Callable[..., None]:
    """Write a settings row directly, bypassing the API."""

    def _put(key: str, value: str, user_id: int | None = None) -> None:
        db.session.add(Setting(key=key, value=value, user_id=user_id))
        db.session.commit()

    return _put
