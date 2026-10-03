"""Endpoint tests for API_SURFACE.md § 2 (current_month)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

import pytest
from flask.testing import FlaskClient
from sqlalchemy import select

from app.extensions import db
from app.models import Budget, Setting, Transaction, User

SWITCH_PATH = "/api/v1/current-month/switch"
STATE_PATH = "/api/v1/current-month"


@pytest.fixture()
def alice(make_user: Callable[..., User]) -> User:
    return make_user("alice")


@pytest.fixture()
def bob(make_user: Callable[..., User]) -> User:
    return make_user("bob")


class TestGetCurrentMonth:
    def test_anonymous_returns_401(self, client: FlaskClient) -> None:
        assert client.get(STATE_PATH).status_code == 401

    def test_envelope_and_defaults(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        response = client.get(STATE_PATH)

        assert response.status_code == 200
        assert response.get_json() == {
            "data": {
                "current_month": "2025-07",
                "last_acknowledged_month": "2025-07",
                "needs_switch": False,
                "earliest_month": None,
            },
            "error": None,
            "meta": None,
        }

    def test_seeded_global_month_flags_a_switch(
        self,
        client: FlaskClient,
        alice: User,
        login: Callable[..., None],
        put_setting: Callable[..., None],
    ) -> None:
        put_setting("last_acknowledged_month", "2025-06")
        login("alice")

        data = client.get(STATE_PATH).get_json()["data"]

        assert data["last_acknowledged_month"] == "2025-06"
        assert data["needs_switch"] is True

    def test_per_user_row_wins_over_the_global_one(
        self,
        client: FlaskClient,
        alice: User,
        login: Callable[..., None],
        put_setting: Callable[..., None],
    ) -> None:
        put_setting("last_acknowledged_month", "2025-04")
        put_setting("last_acknowledged_month", "2025-06", alice.id)
        login("alice")

        data = client.get(STATE_PATH).get_json()["data"]

        assert data["last_acknowledged_month"] == "2025-06"
        assert data["needs_switch"] is True

    def test_each_user_has_their_own_working_month(
        self,
        app: object,
        client: FlaskClient,
        alice: User,
        bob: User,
        put_setting: Callable[..., None],
    ) -> None:
        put_setting("last_acknowledged_month", "2025-06", alice.id)
        put_setting("last_acknowledged_month", "2025-05", bob.id)

        client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "secret-pass"}
        )
        alice_month = client.get(STATE_PATH).get_json()["data"][
            "last_acknowledged_month"
        ]
        client.post("/api/v1/auth/logout")
        client.post(
            "/api/v1/auth/login", json={"username": "bob", "password": "secret-pass"}
        )
        bob_month = client.get(STATE_PATH).get_json()["data"]["last_acknowledged_month"]

        assert (alice_month, bob_month) == ("2025-06", "2025-05")

    def test_earliest_month_is_the_oldest_transaction(
        self,
        client: FlaskClient,
        alice: User,
        login: Callable[..., None],
        make_concept: Callable[..., object],
        make_transaction: Callable[..., Transaction],
    ) -> None:
        concept = make_concept("Groceries", created_by=alice)
        make_transaction(concept=concept, user=alice, amount="10", on=date(2025, 3, 9))
        make_transaction(concept=concept, user=alice, amount="10", on=date(2025, 5, 1))
        login("alice")

        assert client.get(STATE_PATH).get_json()["data"]["earliest_month"] == "2025-03"

    def test_earliest_month_ignores_soft_deleted_transactions(
        self,
        client: FlaskClient,
        alice: User,
        login: Callable[..., None],
        make_concept: Callable[..., object],
        make_transaction: Callable[..., Transaction],
    ) -> None:
        concept = make_concept("Groceries", created_by=alice)
        make_transaction(
            concept=concept,
            user=alice,
            amount="10",
            on=date(2025, 1, 9),
            is_deleted=True,
        )
        make_transaction(concept=concept, user=alice, amount="10", on=date(2025, 3, 9))
        login("alice")

        assert client.get(STATE_PATH).get_json()["data"]["earliest_month"] == "2025-03"


class TestSwitchMonth:
    def test_anonymous_returns_401(self, client: FlaskClient) -> None:
        assert client.post(SWITCH_PATH).status_code == 401

    def test_acknowledging_sets_the_working_month(
        self,
        client: FlaskClient,
        alice: User,
        login: Callable[..., None],
        put_setting: Callable[..., None],
    ) -> None:
        put_setting("last_acknowledged_month", "2025-06")
        login("alice")

        response = client.post(SWITCH_PATH)

        assert response.status_code == 200
        assert response.get_json() == {
            "data": {
                "current_month": "2025-07",
                "last_acknowledged_month": "2025-07",
                "needs_switch": False,
                "earliest_month": None,
            },
            "error": None,
            "meta": None,
        }

    def test_the_switch_survives_a_new_session(
        self,
        client: FlaskClient,
        alice: User,
        login: Callable[..., None],
        put_setting: Callable[..., None],
    ) -> None:
        """BACKEND.md: settings must be persisted, not held in session memory."""
        put_setting("last_acknowledged_month", "2025-06")
        login("alice")
        client.post(SWITCH_PATH)
        client.post("/api/v1/auth/logout")
        login("alice")

        data = client.get(STATE_PATH).get_json()["data"]

        assert data["last_acknowledged_month"] == "2025-07"
        assert data["needs_switch"] is False

    def test_switch_writes_a_per_user_row_and_leaves_the_global_one(
        self,
        client: FlaskClient,
        alice: User,
        login: Callable[..., None],
        put_setting: Callable[..., None],
    ) -> None:
        put_setting("last_acknowledged_month", "2025-06")
        login("alice")
        client.post(SWITCH_PATH)

        rows = db.session.scalars(select(Setting)).all()
        by_owner = {(row.key, row.user_id): row.value for row in rows}

        assert by_owner[("last_acknowledged_month", alice.id)] == "2025-07"
        assert by_owner[("last_acknowledged_month", None)] == "2025-06"

    def test_switching_twice_returns_409(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")
        client.post(SWITCH_PATH)

        response = client.post(SWITCH_PATH)

        assert response.status_code == 409
        assert response.get_json()["error"]["code"] == "CONFLICT"

    def test_switch_when_already_current_returns_409(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        assert client.post(SWITCH_PATH).status_code == 409

    def test_switch_modifies_no_records(
        self,
        client: FlaskClient,
        alice: User,
        login: Callable[..., None],
        make_concept: Callable[..., object],
        make_transaction: Callable[..., Transaction],
        make_budget: Callable[..., Budget],
        put_setting: Callable[..., None],
    ) -> None:
        """BACKEND.md § 3.2: the switch is a state signal, not a data operation."""
        put_setting("last_acknowledged_month", "2025-06")
        concept = make_concept("Rent", created_by=alice)
        transaction = make_transaction(
            concept=concept, user=alice, amount="120.50", on=date(2025, 6, 15)
        )
        budget = make_budget(
            concept=concept, user=alice, amount="900.00", on=date(2025, 1, 31)
        )
        login("alice")

        client.post(SWITCH_PATH)

        db.session.refresh(transaction)
        db.session.refresh(budget)
        assert transaction.date == date(2025, 6, 15)
        assert transaction.is_deleted is False
        assert budget.date == date(2025, 1, 31)
        assert str(budget.amount) == "900.00"
        assert db.session.scalar(select(Transaction)) is not None
