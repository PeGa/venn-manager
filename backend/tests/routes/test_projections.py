"""Endpoint tests for API_SURFACE.md § 5 (projections)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

import pytest
from flask.testing import FlaskClient

from app.extensions import db
from app.models import Budget, Concept, Transaction, User

PATH = "/api/v1/projections"
JULY = "2025-07"
JUNE = "2025-06"

ZERO = {
    "spend_projection": 0.00,
    "earn_projection": 0.00,
    "savings_projection": 0.00,
    "actual_spend": 0.00,
    "actual_earn": 0.00,
    "spend_budget_remaining": 0.00,
    "earn_budget_remaining": 0.00,
}


@pytest.fixture()
def alice(make_user: Callable[..., User]) -> User:
    return make_user("alice")


@pytest.fixture()
def as_alice(client: FlaskClient, alice: User, login: Callable[..., None]) -> User:
    login("alice")
    return alice


@pytest.fixture()
def groceries(make_concept: Callable[..., Concept], alice: User) -> Concept:
    return make_concept("Groceries", flow="out", created_by=alice)


@pytest.fixture()
def rent(make_concept: Callable[..., Concept], alice: User) -> Concept:
    return make_concept("Rent", flow="out", created_by=alice)


@pytest.fixture()
def salary(make_concept: Callable[..., Concept], alice: User) -> Concept:
    return make_concept("Salary", flow="in", created_by=alice)


def get(client: FlaskClient, month: str) -> dict[str, float]:
    response = client.get(f"{PATH}?month={month}")
    assert response.status_code == 200, response.get_json()
    data: dict[str, float] = response.get_json()["data"]
    return data


class TestValidation:
    def test_anonymous_returns_401(self, client: FlaskClient, alice: User) -> None:
        assert client.get(f"{PATH}?month={JULY}").status_code == 401

    def test_missing_month_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        assert client.get(PATH).status_code == 422

    def test_malformed_month_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        for bad in ("2025", "2025-13", "2025-00", "25-07", "tomorrow"):
            assert client.get(f"{PATH}?month={bad}").status_code == 422, bad


class TestEmptyState:
    def test_no_records_is_all_zeros(self, client: FlaskClient, as_alice: User) -> None:
        response = client.get(f"{PATH}?month={JULY}")

        assert response.get_json() == {"data": ZERO, "error": None, "meta": None}

    def test_amounts_are_serialised_with_two_decimals(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        response = client.get(f"{PATH}?month={JULY}")

        assert b'"spend_projection":0.00' in response.data
        assert b'"savings_projection":0.00' in response.data

    def test_the_decomposition_reaches_the_wire_with_two_decimals(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        salary: Concept,
        make_budget: Callable[..., Budget],
        make_transaction: Callable[..., Transaction],
    ) -> None:
        """The reported case: 12 spent + 7 of budget left must be visible as such."""
        make_budget(concept=groceries, user=as_alice, amount="10", on=date(2025, 7, 1))
        make_budget(concept=salary, user=as_alice, amount="100", on=date(2025, 7, 1))
        make_transaction(
            concept=groceries, user=as_alice, amount="3", on=date(2025, 7, 2)
        )

        response = client.get(f"{PATH}?month={JULY}")

        assert b'"spend_budget_remaining":7.00' in response.data
        assert b'"earn_budget_remaining":100.00' in response.data
        assert b'"spend_projection":10.00' in response.data


class TestContractExample:
    def test_matches_the_documented_sample(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        rent: Concept,
        salary: Concept,
        make_budget: Callable[..., Budget],
        make_transaction: Callable[..., Transaction],
    ) -> None:
        """The API_SURFACE.md § 5 sample: spend 1250, earn 3000, save 1750.

        Arithmetic: groceries max(400, 830.50) = 830.50, rent max(419.50, 0) =
        419.50, so spend is 1250.00. Salary min(3000, 3000) = 3000.
        """
        make_budget(concept=groceries, user=as_alice, amount="400", on=date(2025, 7, 1))
        make_budget(concept=rent, user=as_alice, amount="419.50", on=date(2025, 7, 1))
        make_budget(concept=salary, user=as_alice, amount="3000", on=date(2025, 7, 1))
        make_transaction(
            concept=groceries, user=as_alice, amount="830.50", on=date(2025, 7, 5)
        )
        make_transaction(
            concept=salary, user=as_alice, amount="3000", on=date(2025, 7, 1)
        )

        result = get(client, JULY)

        assert result["spend_projection"] == 1250.00
        assert result["earn_projection"] == 3000.00
        assert result["savings_projection"] == 1750.00
        assert result["actual_spend"] == 830.50
        assert result["actual_earn"] == 3000.00


class TestMissingActual:
    """BACKEND.md § 2.2: no transactions is not an actual of zero."""

    def test_budgeted_concepts_with_no_transactions_project_the_budget(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        salary: Concept,
        make_budget: Callable[..., Budget],
    ) -> None:
        """The reported defect: budgets IN=100 and OUT=10, nothing booked yet.

        earn used to read 0 and savings -10, asserting an income shortfall that
        had not happened and making the first day of every month look insolvent.
        """
        make_budget(concept=salary, user=as_alice, amount="100", on=date(2025, 7, 1))
        make_budget(concept=groceries, user=as_alice, amount="10", on=date(2025, 7, 1))

        result = get(client, JULY)

        assert result["earn_projection"] == 100.00
        assert result["spend_projection"] == 10.00
        assert result["savings_projection"] == 90.00
        # The actuals stay honest: nothing has moved yet.
        assert result["actual_earn"] == 0.00
        assert result["actual_spend"] == 0.00

    def test_a_recorded_zero_is_an_actual_and_projects_zero(
        self,
        client: FlaskClient,
        as_alice: User,
        salary: Concept,
        make_budget: Callable[..., Budget],
        make_transaction: Callable[..., Transaction],
    ) -> None:
        make_budget(concept=salary, user=as_alice, amount="100", on=date(2025, 7, 1))
        make_transaction(concept=salary, user=as_alice, amount="0", on=date(2025, 7, 2))

        result = get(client, JULY)

        assert result["earn_projection"] == 0.00
        assert result["actual_earn"] == 0.00

    def test_a_soft_deleted_transaction_counts_as_no_actual(
        self,
        client: FlaskClient,
        as_alice: User,
        salary: Concept,
        make_budget: Callable[..., Budget],
        make_transaction: Callable[..., Transaction],
    ) -> None:
        """A deleted record is not an outcome, so the budget stands again."""
        make_budget(concept=salary, user=as_alice, amount="100", on=date(2025, 7, 1))
        make_transaction(
            concept=salary,
            user=as_alice,
            amount="40",
            on=date(2025, 7, 2),
            is_deleted=True,
        )

        assert get(client, JULY)["earn_projection"] == 100.00


class TestInclusionRules:
    def test_soft_deleted_transactions_are_excluded(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        make_transaction(
            concept=groceries,
            user=as_alice,
            amount="100",
            on=date(2025, 7, 1),
            is_deleted=True,
        )

        assert get(client, JULY) == ZERO

    def test_soft_deleted_budgets_are_excluded(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_budget: Callable[..., Budget],
    ) -> None:
        make_budget(
            concept=groceries,
            user=as_alice,
            amount="100",
            on=date(2025, 7, 1),
            is_deleted=True,
        )

        assert get(client, JULY) == ZERO

    def test_transactions_outside_the_month_are_excluded(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        make_transaction(
            concept=groceries, user=as_alice, amount="100", on=date(2025, 6, 30)
        )
        make_transaction(
            concept=groceries, user=as_alice, amount="100", on=date(2025, 8, 1)
        )

        assert get(client, JULY) == ZERO

    def test_budgets_from_other_months_still_count(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_budget: Callable[..., Budget],
    ) -> None:
        """BACKEND.md § 2.1: budgets persist and are not month-filtered."""
        make_budget(
            concept=groceries, user=as_alice, amount="300", on=date(2024, 11, 3)
        )

        assert get(client, JULY)["spend_projection"] == 300.00

    def test_a_null_budget_amount_counts_as_zero(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_budget: Callable[..., Budget],
    ) -> None:
        make_budget(concept=groceries, user=as_alice, amount=None, on=date(2025, 7, 1))

        assert get(client, JULY) == ZERO

    def test_month_boundaries_are_inclusive(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        make_transaction(
            concept=groceries, user=as_alice, amount="10", on=date(2025, 7, 1)
        )
        make_transaction(
            concept=groceries, user=as_alice, amount="15", on=date(2025, 7, 31)
        )

        result = get(client, JULY)

        assert result["actual_spend"] == 25.00


class TestGhostConcepts:
    def test_working_month_ignores_a_deleted_concepts_transactions(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        make_transaction(
            concept=groceries, user=as_alice, amount="100", on=date(2025, 7, 1)
        )
        groceries.is_deleted = True
        db.session.commit()

        assert get(client, JULY) == ZERO

    def test_previous_month_keeps_them_as_unbudgeted(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_budget: Callable[..., Budget],
        make_transaction: Callable[..., Transaction],
    ) -> None:
        """BACKEND.md § 1.2: the budget is gone, the spending still counts."""
        make_budget(concept=groceries, user=as_alice, amount="500", on=date(2025, 6, 1))
        make_transaction(
            concept=groceries, user=as_alice, amount="100", on=date(2025, 6, 1)
        )
        groceries.is_deleted = True
        db.session.commit()

        result = get(client, JUNE)

        assert result["spend_projection"] == 100.00
        assert result["actual_spend"] == 100.00

    def test_a_deleted_concepts_budget_never_counts(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_budget: Callable[..., Budget],
    ) -> None:
        make_budget(concept=groceries, user=as_alice, amount="500", on=date(2025, 7, 1))
        groceries.is_deleted = True
        db.session.commit()

        assert get(client, JULY) == ZERO
        assert get(client, JUNE) == ZERO

    def test_switching_the_working_month_changes_the_rule(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
        put_setting: Callable[..., None],
    ) -> None:
        """The rule keys on the *requesting user's* working month, not today."""
        make_transaction(
            concept=groceries, user=as_alice, amount="100", on=date(2025, 7, 1)
        )
        groceries.is_deleted = True
        db.session.commit()

        assert get(client, JULY) == ZERO

        put_setting("last_acknowledged_month", "2025-08", as_alice.id)

        assert get(client, JULY)["actual_spend"] == 100.00


class TestPerUserWorkingMonth:
    def test_each_user_projects_with_their_own_working_month(
        self,
        app: object,
        client: FlaskClient,
        alice: User,
        make_user: Callable[..., User],
        make_concept: Callable[..., Concept],
        make_transaction: Callable[..., Transaction],
        put_setting: Callable[..., None],
    ) -> None:
        concept = make_concept("Groceries", flow="out", created_by=alice)
        make_transaction(concept=concept, user=alice, amount="100", on=date(2025, 7, 1))
        concept.is_deleted = True
        db.session.commit()
        bob = make_user("bob")
        put_setting("last_acknowledged_month", "2025-08", bob.id)

        client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "secret-pass"}
        )
        alice_view = get(client, JULY)["actual_spend"]
        client.post("/api/v1/auth/logout")
        client.post(
            "/api/v1/auth/login", json={"username": "bob", "password": "secret-pass"}
        )
        bob_view = get(client, JULY)["actual_spend"]

        assert (alice_view, bob_view) == (0.00, 100.00)
