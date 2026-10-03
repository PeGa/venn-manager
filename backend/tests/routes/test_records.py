"""Endpoint tests for API_SURFACE.md § 4 (records)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

import pytest
from flask.testing import FlaskClient

from app.extensions import db
from app.models import Budget, Concept, Transaction, User

PATH = "/api/v1/records"
JULY = "2025-07"
JUNE = "2025-06"

RECORD_KEYS = {
    "id",
    "type",
    "date",
    "concept_id",
    "concept_name",
    "concept_flow",
    "concept_is_deleted",
    "amount",
    "user_id",
    "username",
    "user_is_deleted",
    "created_at",
}


@pytest.fixture()
def alice(make_user: Callable[..., User]) -> User:
    return make_user("alice", real_name="Alice Doe")


@pytest.fixture()
def as_alice(client: FlaskClient, alice: User, login: Callable[..., None]) -> User:
    login("alice")
    return alice


@pytest.fixture()
def groceries(make_concept: Callable[..., Concept], alice: User) -> Concept:
    return make_concept("Groceries", flow="out", created_by=alice)


@pytest.fixture()
def salary(make_concept: Callable[..., Concept], alice: User) -> Concept:
    return make_concept("Salary", flow="in", created_by=alice)


class TestListTransactions:
    def test_anonymous_returns_401(self, client: FlaskClient, alice: User) -> None:
        assert client.get(f"{PATH}?type=transaction&month={JULY}").status_code == 401

    def test_missing_type_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        assert client.get(f"{PATH}?month={JULY}").status_code == 422

    def test_unknown_type_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        assert client.get(f"{PATH}?type=invoice&month={JULY}").status_code == 422

    def test_missing_month_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        assert client.get(f"{PATH}?type=transaction").status_code == 422

    def test_malformed_month_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        assert client.get(f"{PATH}?type=transaction&month=2025-7").status_code == 422
        assert client.get(f"{PATH}?type=transaction&month=2025-13").status_code == 422

    def test_record_shape(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        make_transaction(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 15)
        )

        response = client.get(f"{PATH}?type=transaction&month={JULY}")

        assert response.status_code == 200
        body = response.get_json()
        assert set(body["data"][0]) == RECORD_KEYS
        assert body["data"][0] == {
            "id": 1,
            "type": "transaction",
            "date": "2025-07-15",
            "concept_id": groceries.id,
            "concept_name": "Groceries",
            "concept_flow": "out",
            "concept_is_deleted": False,
            "amount": 45.50,
            "user_id": as_alice.id,
            "username": "alice",
            "user_is_deleted": False,
            "created_at": body["data"][0]["created_at"],
        }
        assert body["meta"] == {
            "page": 1,
            "per_page": 10,
            "total": 1,
            "total_pages": 1,
        }

    def test_amount_is_serialised_with_two_decimals(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        make_transaction(
            concept=groceries, user=as_alice, amount="45.5", on=date(2025, 7, 1)
        )

        assert (
            b'"amount":45.50'
            in client.get(f"{PATH}?type=transaction&month={JULY}").data
        )

    def test_only_the_requested_month_is_returned(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        make_transaction(
            concept=groceries, user=as_alice, amount="10", on=date(2025, 6, 30)
        )
        make_transaction(
            concept=groceries, user=as_alice, amount="20", on=date(2025, 7, 1)
        )

        data = client.get(f"{PATH}?type=transaction&month={JULY}").get_json()["data"]

        assert [row["amount"] for row in data] == [20.00]

    def test_soft_deleted_records_are_never_returned(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        make_transaction(
            concept=groceries,
            user=as_alice,
            amount="10",
            on=date(2025, 7, 1),
            is_deleted=True,
        )

        assert (
            client.get(f"{PATH}?type=transaction&month={JULY}").get_json()["data"] == []
        )

    def test_working_month_hides_a_deleted_concepts_records(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        """BACKEND.md § 1.2: the ghost rule for the working month."""
        make_transaction(
            concept=groceries, user=as_alice, amount="10", on=date(2025, 7, 1)
        )
        groceries.is_deleted = True
        db.session.commit()

        data = client.get(f"{PATH}?type=transaction&month={JULY}").get_json()["data"]

        assert data == []

    def test_previous_month_keeps_a_deleted_concepts_records(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        """BACKEND.md § 1.2: history is never rewritten."""
        make_transaction(
            concept=groceries, user=as_alice, amount="10", on=date(2025, 6, 1)
        )
        groceries.is_deleted = True
        db.session.commit()

        data = client.get(f"{PATH}?type=transaction&month={JUNE}").get_json()["data"]

        assert len(data) == 1
        assert data[0]["concept_is_deleted"] is True
        assert data[0]["concept_name"] == "Groceries"

    def test_a_deleted_user_is_flagged(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_user: Callable[..., User],
        make_transaction: Callable[..., Transaction],
        login: Callable[..., None],
    ) -> None:
        author = make_user("author")
        make_transaction(
            concept=groceries, user=author, amount="10", on=date(2025, 7, 1)
        )
        author.is_deleted = True
        db.session.commit()

        data = client.get(f"{PATH}?type=transaction&month={JULY}").get_json()["data"]

        assert data[0]["username"] == "author"
        assert data[0]["user_is_deleted"] is True

    def test_search_matches_a_substring_of_the_concept_name(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        salary: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        make_transaction(
            concept=groceries, user=as_alice, amount="10", on=date(2025, 7, 1)
        )
        make_transaction(
            concept=salary, user=as_alice, amount="20", on=date(2025, 7, 2)
        )

        data = client.get(
            f"{PATH}?type=transaction&month={JULY}&search=rocer"
        ).get_json()["data"]

        assert [row["concept_name"] for row in data] == ["Groceries"]

    def test_search_is_case_insensitive(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        make_transaction(
            concept=groceries, user=as_alice, amount="10", on=date(2025, 7, 1)
        )

        data = client.get(
            f"{PATH}?type=transaction&month={JULY}&search=GROCERIES"
        ).get_json()["data"]

        assert len(data) == 1

    def test_search_does_not_cross_the_month_boundary(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        """FRONTEND.md appendix: a filter never carries results from another month."""
        make_transaction(
            concept=groceries, user=as_alice, amount="10", on=date(2025, 6, 1)
        )

        data = client.get(
            f"{PATH}?type=transaction&month={JULY}&search=Groceries"
        ).get_json()["data"]

        assert data == []

    def test_like_wildcards_are_escaped(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        make_transaction(
            concept=groceries, user=as_alice, amount="10", on=date(2025, 7, 1)
        )

        data = client.get(
            f"{PATH}?type=transaction&month={JULY}&search=%25"
        ).get_json()["data"]

        assert data == []

    def test_results_are_sorted_by_id(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        salary: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        make_transaction(concept=salary, user=as_alice, amount="1", on=date(2025, 7, 5))
        make_transaction(
            concept=groceries, user=as_alice, amount="2", on=date(2025, 7, 1)
        )

        ids = [
            row["id"]
            for row in client.get(f"{PATH}?type=transaction&month={JULY}").get_json()[
                "data"
            ]
        ]

        assert ids == sorted(ids)


class TestListPagination:
    @pytest.fixture()
    def twelve(
        self,
        groceries: Concept,
        alice: User,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        for index in range(12):
            make_transaction(
                concept=groceries,
                user=alice,
                amount="1",
                on=date(2025, 7, index + 1),
            )

    def test_default_page_size_is_ten(
        self, client: FlaskClient, as_alice: User, twelve: None
    ) -> None:
        body = client.get(f"{PATH}?type=transaction&month={JULY}").get_json()

        assert len(body["data"]) == 10
        assert body["meta"] == {
            "page": 1,
            "per_page": 10,
            "total": 12,
            "total_pages": 2,
        }

    def test_second_page(
        self, client: FlaskClient, as_alice: User, twelve: None
    ) -> None:
        body = client.get(f"{PATH}?type=transaction&month={JULY}&page=2").get_json()

        assert len(body["data"]) == 2
        assert body["meta"]["page"] == 2

    def test_page_size_is_selectable(
        self, client: FlaskClient, as_alice: User, twelve: None
    ) -> None:
        assert (
            len(
                client.get(f"{PATH}?type=transaction&month={JULY}&q=20").get_json()[
                    "data"
                ]
            )
            == 12
        )
        assert (
            len(
                client.get(f"{PATH}?type=transaction&month={JULY}&q=50").get_json()[
                    "data"
                ]
            )
            == 12
        )

    def test_q_all_reports_total_as_page_size(
        self, client: FlaskClient, as_alice: User, twelve: None
    ) -> None:
        """API_SURFACE.md § Pagination: with q=all, per_page equals total."""
        body = client.get(f"{PATH}?type=transaction&month={JULY}&q=all").get_json()

        assert len(body["data"]) == 12
        assert body["meta"] == {
            "page": 1,
            "per_page": 12,
            "total": 12,
            "total_pages": 1,
        }

    def test_unlisted_page_size_returns_422(
        self, client: FlaskClient, as_alice: User, twelve: None
    ) -> None:
        assert (
            client.get(f"{PATH}?type=transaction&month={JULY}&q=15").status_code == 422
        )

    def test_page_zero_returns_422(
        self, client: FlaskClient, as_alice: User, twelve: None
    ) -> None:
        assert (
            client.get(f"{PATH}?type=transaction&month={JULY}&page=0").status_code
            == 422
        )

    def test_non_numeric_page_returns_422(
        self, client: FlaskClient, as_alice: User, twelve: None
    ) -> None:
        assert (
            client.get(f"{PATH}?type=transaction&month={JULY}&page=abc").status_code
            == 422
        )

    def test_page_past_the_end_is_empty(
        self, client: FlaskClient, as_alice: User, twelve: None
    ) -> None:
        body = client.get(f"{PATH}?type=transaction&month={JULY}&page=9").get_json()

        assert body["data"] == []
        assert body["meta"]["total"] == 12

    def test_empty_list_meta(self, client: FlaskClient, as_alice: User) -> None:
        body = client.get(f"{PATH}?type=transaction&month={JULY}").get_json()

        assert body["data"] == []
        assert body["meta"] == {
            "page": 1,
            "per_page": 10,
            "total": 0,
            "total_pages": 1,
        }


class TestListBudgets:
    def test_month_is_ignored(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_budget: Callable[..., Budget],
    ) -> None:
        """Budgets are a standing list (API_SURFACE.md § GET /records)."""
        make_budget(
            concept=groceries, user=as_alice, amount="500", on=date(2024, 1, 31)
        )

        data = client.get(f"{PATH}?type=budget&month={JULY}").get_json()["data"]

        assert len(data) == 1
        assert data[0]["date"] == "2024-01-31"

    def test_month_is_not_required(self, client: FlaskClient, as_alice: User) -> None:
        assert client.get(f"{PATH}?type=budget").status_code == 200

    def test_amount_may_be_null(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_budget: Callable[..., Budget],
    ) -> None:
        make_budget(concept=groceries, user=as_alice, amount=None, on=date(2025, 7, 1))

        data = client.get(f"{PATH}?type=budget").get_json()["data"]

        assert data[0]["amount"] is None

    def test_deleted_concepts_budgets_always_disappear(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_budget: Callable[..., Budget],
    ) -> None:
        make_budget(concept=groceries, user=as_alice, amount="500", on=date(2025, 7, 1))
        groceries.is_deleted = True
        db.session.commit()

        assert client.get(f"{PATH}?type=budget").get_json()["data"] == []

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
            amount="500",
            on=date(2025, 7, 1),
            is_deleted=True,
        )

        assert client.get(f"{PATH}?type=budget").get_json()["data"] == []

    def test_search_filters_budgets(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        salary: Concept,
        make_budget: Callable[..., Budget],
    ) -> None:
        make_budget(concept=groceries, user=as_alice, amount="1", on=date(2025, 7, 1))
        make_budget(concept=salary, user=as_alice, amount="2", on=date(2025, 7, 1))

        data = client.get(f"{PATH}?type=budget&search=Sal").get_json()["data"]

        assert [row["concept_name"] for row in data] == ["Salary"]


class TestCreateRecord:
    def test_creates_a_transaction(
        self, client: FlaskClient, as_alice: User, groceries: Concept
    ) -> None:
        response = client.post(
            PATH,
            json={
                "type": "transaction",
                "date": "2025-07-15",
                "concept_id": groceries.id,
                "amount": 45.50,
            },
        )

        assert response.status_code == 201
        data = response.get_json()["data"]
        assert set(data) == RECORD_KEYS
        assert data["type"] == "transaction"
        assert data["concept_flow"] == "out"
        assert data["user_id"] == as_alice.id
        assert data["username"] == "alice"
        assert b'"amount":45.50' in response.data

    def test_creates_a_budget_without_an_amount(
        self, client: FlaskClient, as_alice: User, groceries: Concept
    ) -> None:
        response = client.post(
            PATH,
            json={"type": "budget", "date": "2025-07-15", "concept_id": groceries.id},
        )

        assert response.status_code == 201
        assert response.get_json()["data"]["amount"] is None

    def test_creates_a_budget_with_a_null_amount(
        self, client: FlaskClient, as_alice: User, groceries: Concept
    ) -> None:
        response = client.post(
            PATH,
            json={
                "type": "budget",
                "date": "2025-07-15",
                "concept_id": groceries.id,
                "amount": None,
            },
        )

        assert response.status_code == 201
        assert response.get_json()["data"]["amount"] is None

    def test_flow_is_taken_from_the_concept_not_the_body(
        self, client: FlaskClient, as_alice: User, groceries: Concept
    ) -> None:
        """BACKEND.md § 5.1: a mismatched flow in the body is ignored."""
        response = client.post(
            PATH,
            json={
                "type": "transaction",
                "date": "2025-07-15",
                "concept_id": groceries.id,
                "amount": 10,
                "flow": "in",
            },
        )

        assert response.status_code == 201
        assert response.get_json()["data"]["concept_flow"] == "out"

    def test_a_numeric_string_amount_is_accepted(
        self, client: FlaskClient, as_alice: User, groceries: Concept
    ) -> None:
        response = client.post(
            PATH,
            json={
                "type": "transaction",
                "date": "2025-07-15",
                "concept_id": groceries.id,
                "amount": "45.50",
            },
        )

        assert response.status_code == 201
        assert b'"amount":45.50' in response.data

    def test_missing_amount_for_a_transaction_returns_422(
        self, client: FlaskClient, as_alice: User, groceries: Concept
    ) -> None:
        response = client.post(
            PATH,
            json={
                "type": "transaction",
                "date": "2025-07-15",
                "concept_id": groceries.id,
            },
        )

        assert response.status_code == 422
        assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_deleted_concept_returns_422(
        self,
        client: FlaskClient,
        as_alice: User,
        make_concept: Callable[..., Concept],
    ) -> None:
        gone = make_concept("Gone", flow="out", created_by=as_alice, is_deleted=True)

        response = client.post(
            PATH,
            json={
                "type": "transaction",
                "date": "2025-07-15",
                "concept_id": gone.id,
                "amount": 10,
            },
        )

        assert response.status_code == 422

    def test_unknown_concept_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        response = client.post(
            PATH,
            json={
                "type": "transaction",
                "date": "2025-07-15",
                "concept_id": 999,
                "amount": 10,
            },
        )

        assert response.status_code == 422

    def test_invalid_date_returns_422(
        self, client: FlaskClient, as_alice: User, groceries: Concept
    ) -> None:
        for bad in ("15/07/2025", "2025-02-30", "2025-7-15", "yesterday"):
            response = client.post(
                PATH,
                json={
                    "type": "transaction",
                    "date": bad,
                    "concept_id": groceries.id,
                    "amount": 10,
                },
            )

            assert response.status_code == 422, bad

    def test_excessive_decimal_precision_returns_422(
        self, client: FlaskClient, as_alice: User, groceries: Concept
    ) -> None:
        response = client.post(
            PATH,
            json={
                "type": "transaction",
                "date": "2025-07-15",
                "concept_id": groceries.id,
                "amount": 45.567,
            },
        )

        assert response.status_code == 422

    def test_non_numeric_amount_returns_422(
        self, client: FlaskClient, as_alice: User, groceries: Concept
    ) -> None:
        response = client.post(
            PATH,
            json={
                "type": "transaction",
                "date": "2025-07-15",
                "concept_id": groceries.id,
                "amount": "lots",
            },
        )

        assert response.status_code == 422

    def test_boolean_amount_returns_422(
        self, client: FlaskClient, as_alice: User, groceries: Concept
    ) -> None:
        response = client.post(
            PATH,
            json={
                "type": "transaction",
                "date": "2025-07-15",
                "concept_id": groceries.id,
                "amount": True,
            },
        )

        assert response.status_code == 422

    def test_missing_type_returns_422(
        self, client: FlaskClient, as_alice: User, groceries: Concept
    ) -> None:
        response = client.post(
            PATH, json={"date": "2025-07-15", "concept_id": groceries.id, "amount": 10}
        )

        assert response.status_code == 422

    def test_missing_concept_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        response = client.post(
            PATH, json={"type": "transaction", "date": "2025-07-15", "amount": 10}
        )

        assert response.status_code == 422

    def test_user_id_from_the_body_is_ignored(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_user: Callable[..., User],
    ) -> None:
        other = make_user("other")

        response = client.post(
            PATH,
            json={
                "type": "transaction",
                "date": "2025-07-15",
                "concept_id": groceries.id,
                "amount": 10,
                "user_id": other.id,
            },
        )

        assert response.get_json()["data"]["user_id"] == as_alice.id


class TestUpdateRecord:
    def test_amount_is_updated(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        record = make_transaction(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 1)
        )

        response = client.patch(
            f"{PATH}/{record.id}?type=transaction", json={"amount": "52.00"}
        )

        assert response.status_code == 200
        assert b'"amount":52.00' in response.data

    def test_concept_change_moves_the_flow(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        salary: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        record = make_transaction(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 1)
        )

        response = client.patch(
            f"{PATH}/{record.id}?type=transaction", json={"concept_id": salary.id}
        )

        assert response.get_json()["data"]["concept_flow"] == "in"
        assert response.get_json()["data"]["concept_name"] == "Salary"

    def test_budget_amount_can_be_cleared(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_budget: Callable[..., Budget],
    ) -> None:
        record = make_budget(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 1)
        )

        response = client.patch(
            f"{PATH}/{record.id}?type=budget", json={"amount": None}
        )

        assert response.status_code == 200
        assert response.get_json()["data"]["amount"] is None

    def test_missing_type_returns_422(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        record = make_transaction(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 1)
        )

        assert (
            client.patch(f"{PATH}/{record.id}", json={"amount": 1}).status_code == 422
        )

    def test_empty_body_returns_422(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        record = make_transaction(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 1)
        )

        assert (
            client.patch(f"{PATH}/{record.id}?type=transaction", json={}).status_code
            == 422
        )

    def test_unknown_field_returns_422(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        record = make_transaction(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 1)
        )

        response = client.patch(
            f"{PATH}/{record.id}?type=transaction", json={"flow": "in"}
        )

        assert response.status_code == 422

    def test_wrong_type_returns_404(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        record = make_transaction(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 1)
        )

        response = client.patch(f"{PATH}/{record.id}?type=budget", json={"amount": 1})

        assert response.status_code == 404
        assert response.get_json()["error"]["code"] == "NOT_FOUND"

    def test_unknown_id_returns_404(self, client: FlaskClient, as_alice: User) -> None:
        assert (
            client.patch(f"{PATH}/999?type=transaction", json={"amount": 1}).status_code
            == 404
        )

    def test_soft_deleted_record_returns_410(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        record = make_transaction(
            concept=groceries,
            user=as_alice,
            amount="45.50",
            on=date(2025, 7, 1),
            is_deleted=True,
        )

        response = client.patch(
            f"{PATH}/{record.id}?type=transaction", json={"amount": 1}
        )

        assert response.status_code == 410
        assert response.get_json()["error"] == {
            "code": "GONE",
            "message": "Record not available anymore.",
        }

    def test_deleted_concept_returns_410(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        """BACKEND.md § 1.2: records of a deleted concept cannot be edited."""
        record = make_transaction(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 1)
        )
        groceries.is_deleted = True
        db.session.commit()

        response = client.patch(
            f"{PATH}/{record.id}?type=transaction", json={"amount": 1}
        )

        assert response.status_code == 410

    def test_clearing_a_transaction_amount_returns_422(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        record = make_transaction(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 1)
        )

        response = client.patch(
            f"{PATH}/{record.id}?type=transaction", json={"amount": None}
        )

        assert response.status_code == 422

    def test_switching_to_a_deleted_concept_returns_422(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_concept: Callable[..., Concept],
        make_transaction: Callable[..., Transaction],
    ) -> None:
        record = make_transaction(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 1)
        )
        gone = make_concept("Gone", flow="out", created_by=as_alice, is_deleted=True)

        response = client.patch(
            f"{PATH}/{record.id}?type=transaction", json={"concept_id": gone.id}
        )

        assert response.status_code == 422

    def test_invalid_date_returns_422(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        record = make_transaction(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 1)
        )

        response = client.patch(
            f"{PATH}/{record.id}?type=transaction", json={"date": "2025-13-01"}
        )

        assert response.status_code == 422


class TestDeleteRecord:
    def test_soft_deletes(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        record = make_transaction(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 1)
        )

        response = client.delete(f"{PATH}/{record.id}?type=transaction")

        assert response.status_code == 200
        assert response.get_json() == {"data": None, "error": None, "meta": None}
        db.session.refresh(record)
        assert record.is_deleted is True

    def test_deleted_record_leaves_the_list(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        record = make_transaction(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 1)
        )
        client.delete(f"{PATH}/{record.id}?type=transaction")

        assert (
            client.get(f"{PATH}?type=transaction&month={JULY}").get_json()["data"] == []
        )

    def test_missing_type_returns_422(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        record = make_transaction(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 1)
        )

        assert client.delete(f"{PATH}/{record.id}").status_code == 422

    def test_unknown_id_returns_404(self, client: FlaskClient, as_alice: User) -> None:
        assert client.delete(f"{PATH}/999?type=transaction").status_code == 404

    def test_already_deleted_returns_410(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        record = make_transaction(
            concept=groceries,
            user=as_alice,
            amount="45.50",
            on=date(2025, 7, 1),
            is_deleted=True,
        )

        response = client.delete(f"{PATH}/{record.id}?type=transaction")

        assert response.status_code == 410

    def test_deleted_concept_returns_410(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        record = make_transaction(
            concept=groceries, user=as_alice, amount="45.50", on=date(2025, 7, 1)
        )
        groceries.is_deleted = True
        db.session.commit()

        assert client.delete(f"{PATH}/{record.id}?type=transaction").status_code == 410

    def test_any_user_may_delete_another_users_record(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_user: Callable[..., User],
        make_transaction: Callable[..., Transaction],
    ) -> None:
        """FRONTEND.md: peers act by agreement, so deletion is not ownership-gated."""
        other = make_user("other")
        record = make_transaction(
            concept=groceries, user=other, amount="45.50", on=date(2025, 7, 1)
        )

        assert client.delete(f"{PATH}/{record.id}?type=transaction").status_code == 200


class TestBulkDeleteRecords:
    def test_deletes_all_listed_ids(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        first = make_transaction(
            concept=groceries, user=as_alice, amount="1", on=date(2025, 7, 1)
        )
        second = make_transaction(
            concept=groceries, user=as_alice, amount="2", on=date(2025, 7, 2)
        )

        response = client.delete(f"{PATH}?type=transaction&ids={first.id},{second.id}")

        assert response.status_code == 200
        assert response.get_json() == {
            "data": {"deleted": 2},
            "error": None,
            "meta": None,
        }

    def test_missing_type_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        assert client.delete(f"{PATH}?ids=1").status_code == 422

    def test_missing_ids_returns_422(self, client: FlaskClient, as_alice: User) -> None:
        assert client.delete(f"{PATH}?type=transaction").status_code == 422

    def test_more_than_one_hundred_ids_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        ids = ",".join(str(i) for i in range(1, 102))

        assert client.delete(f"{PATH}?type=transaction&ids={ids}").status_code == 422

    def test_unknown_id_returns_404_and_changes_nothing(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        first = make_transaction(
            concept=groceries, user=as_alice, amount="1", on=date(2025, 7, 1)
        )

        response = client.delete(f"{PATH}?type=transaction&ids={first.id},999")

        assert response.status_code == 404
        db.session.refresh(first)
        assert first.is_deleted is False

    def test_already_deleted_id_returns_410(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_transaction: Callable[..., Transaction],
    ) -> None:
        first = make_transaction(
            concept=groceries, user=as_alice, amount="1", on=date(2025, 7, 1)
        )
        gone = make_transaction(
            concept=groceries,
            user=as_alice,
            amount="2",
            on=date(2025, 7, 2),
            is_deleted=True,
        )

        response = client.delete(f"{PATH}?type=transaction&ids={first.id},{gone.id}")

        assert response.status_code == 410
        db.session.refresh(first)
        assert first.is_deleted is False

    def test_ids_of_the_other_type_return_404(
        self,
        client: FlaskClient,
        as_alice: User,
        groceries: Concept,
        make_budget: Callable[..., Budget],
    ) -> None:
        budget = make_budget(
            concept=groceries, user=as_alice, amount="1", on=date(2025, 7, 1)
        )

        response = client.delete(f"{PATH}?type=transaction&ids={budget.id}")

        assert response.status_code == 404
