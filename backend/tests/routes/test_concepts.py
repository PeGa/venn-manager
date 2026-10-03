"""Endpoint tests for API_SURFACE.md § 3.3 (concept management)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

import pytest
from flask.testing import FlaskClient

from app.extensions import db
from app.models import Budget, Concept, Transaction, User

PATH = "/api/v1/settings/concepts"


@pytest.fixture()
def alice(make_user: Callable[..., User]) -> User:
    return make_user("alice", real_name="Alice Doe")


@pytest.fixture()
def as_alice(client: FlaskClient, alice: User, login: Callable[..., None]) -> User:
    login("alice")
    return alice


def _create(client: FlaskClient, name: str, flow: str) -> dict[str, object]:
    response = client.post(PATH, json={"name": name, "flow": flow})
    assert response.status_code == 201, response.get_json()
    data: dict[str, object] = response.get_json()["data"]
    return data


class TestListConcepts:
    def test_anonymous_returns_401(self, client: FlaskClient, alice: User) -> None:
        assert client.get(PATH).status_code == 401

    def test_empty_list_has_null_meta(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        """Concepts are a small reference list and are never paginated."""
        response = client.get(PATH)

        assert response.status_code == 200
        assert response.get_json() == {"data": [], "error": None, "meta": None}

    def test_item_shape(self, client: FlaskClient, as_alice: User) -> None:
        created = _create(client, "Groceries", "out")

        listed = client.get(PATH).get_json()["data"][0]

        assert set(listed) == {
            "id",
            "name",
            "flow",
            "created_by",
            "created_by_is_deleted",
            "created_at",
            "is_deleted",
        }
        assert listed["id"] == created["id"]
        assert listed["created_by"] == "alice"
        assert listed["created_by_is_deleted"] is False
        assert listed["is_deleted"] is False
        assert listed["created_at"].endswith("Z")

    def test_soft_deleted_are_excluded_by_default(
        self,
        client: FlaskClient,
        as_alice: User,
        make_concept: Callable[..., Concept],
    ) -> None:
        make_concept("Groceries")
        make_concept("Gone", is_deleted=True)

        names = [c["name"] for c in client.get(PATH).get_json()["data"]]

        assert names == ["Groceries"]

    def test_include_deleted_returns_them_flagged(
        self,
        client: FlaskClient,
        as_alice: User,
        make_concept: Callable[..., Concept],
    ) -> None:
        make_concept("Gone", is_deleted=True)

        data = client.get(f"{PATH}?include_deleted=true").get_json()["data"]

        assert data[0]["is_deleted"] is True
        assert data[0]["name"] == "Gone"

    def test_flow_filter(self, client: FlaskClient, as_alice: User) -> None:
        _create(client, "Groceries", "out")
        _create(client, "Salary", "in")

        data = client.get(f"{PATH}?flow=in").get_json()["data"]

        assert [c["name"] for c in data] == ["Salary"]

    def test_invalid_flow_filter_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        assert client.get(f"{PATH}?flow=sideways").status_code == 422

    def test_list_is_sorted_by_id(self, client: FlaskClient, as_alice: User) -> None:
        _create(client, "B", "out")
        _create(client, "A", "out")

        ids = [c["id"] for c in client.get(PATH).get_json()["data"]]

        assert ids == sorted(ids)

    def test_deleted_creator_is_flagged(
        self,
        client: FlaskClient,
        make_user: Callable[..., User],
        make_concept: Callable[..., Concept],
        login: Callable[..., None],
    ) -> None:
        creator = make_user("creator")
        viewer = make_user("viewer")
        make_concept("Groceries", created_by=creator)
        creator.is_deleted = True
        db.session.commit()
        login("viewer")

        data = client.get(PATH).get_json()["data"]

        assert data[0]["created_by"] == "creator"
        assert data[0]["created_by_is_deleted"] is True
        assert viewer.id != creator.id


class TestCreateConcept:
    def test_creates_and_returns_201(self, client: FlaskClient, as_alice: User) -> None:
        response = client.post(PATH, json={"name": "Rent", "flow": "out"})

        assert response.status_code == 201
        data = response.get_json()["data"]
        assert data["name"] == "Rent"
        assert data["flow"] == "out"
        assert data["created_by"] == "alice"
        assert data["is_deleted"] is False
        assert response.get_json()["meta"] is None

    def test_any_user_may_create(
        self,
        client: FlaskClient,
        as_alice: User,
        make_user: Callable[..., User],
    ) -> None:
        """Only user management is admin-gated; concepts are not."""
        assert (
            client.post(PATH, json={"name": "Rent", "flow": "out"}).status_code == 201
        )

    def test_same_name_different_flow_is_allowed(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        _create(client, "Transfer", "out")

        response = client.post(PATH, json={"name": "Transfer", "flow": "in"})

        assert response.status_code == 201

    def test_duplicate_name_and_flow_returns_409(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        _create(client, "Rent", "out")

        response = client.post(PATH, json={"name": "Rent", "flow": "out"})

        assert response.status_code == 409
        assert response.get_json()["error"]["code"] == "CONFLICT"

    def test_deleted_concept_name_can_be_reused(
        self,
        client: FlaskClient,
        as_alice: User,
        make_concept: Callable[..., Concept],
    ) -> None:
        make_concept("Rent", flow="out", is_deleted=True)

        response = client.post(PATH, json={"name": "Rent", "flow": "out"})

        assert response.status_code == 201

    def test_name_is_trimmed(self, client: FlaskClient, as_alice: User) -> None:
        data = _create(client, "  Rent  ", "out")

        assert data["name"] == "Rent"

    def test_empty_name_returns_422(self, client: FlaskClient, as_alice: User) -> None:
        response = client.post(PATH, json={"name": "   ", "flow": "out"})

        assert response.status_code == 422
        assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_overlong_name_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        response = client.post(PATH, json={"name": "x" * 65, "flow": "out"})

        assert response.status_code == 422

    def test_invalid_flow_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        assert client.post(PATH, json={"name": "Rent", "flow": "up"}).status_code == 422

    def test_missing_flow_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        assert client.post(PATH, json={"name": "Rent"}).status_code == 422


class TestRenameConcept:
    def test_rename_returns_200(self, client: FlaskClient, as_alice: User) -> None:
        created = _create(client, "Rent", "out")

        response = client.patch(
            f"{PATH}/{created['id']}", json={"name": "Monthly Rent"}
        )

        assert response.status_code == 200
        assert response.get_json()["data"]["name"] == "Monthly Rent"
        assert response.get_json()["data"]["flow"] == "out"

    def test_rename_is_visible_in_the_list(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        created = _create(client, "Rent", "out")
        client.patch(f"{PATH}/{created['id']}", json={"name": "Monthly Rent"})

        names = [c["name"] for c in client.get(PATH).get_json()["data"]]

        assert names == ["Monthly Rent"]

    def test_renaming_to_the_same_name_is_allowed(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        created = _create(client, "Rent", "out")

        response = client.patch(f"{PATH}/{created['id']}", json={"name": "Rent"})

        assert response.status_code == 200

    def test_colliding_with_another_concept_returns_409(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        _create(client, "Rent", "out")
        other = _create(client, "Food", "out")

        response = client.patch(f"{PATH}/{other['id']}", json={"name": "Rent"})

        assert response.status_code == 409

    def test_collision_ignores_deleted_concepts(
        self,
        client: FlaskClient,
        as_alice: User,
        make_concept: Callable[..., Concept],
    ) -> None:
        make_concept("Rent", flow="out", is_deleted=True)
        other = _create(client, "Food", "out")

        response = client.patch(f"{PATH}/{other['id']}", json={"name": "Rent"})

        assert response.status_code == 200

    def test_changing_flow_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        """API_SURFACE.md § PATCH concepts: flow is immutable."""
        created = _create(client, "Rent", "out")

        response = client.patch(
            f"{PATH}/{created['id']}", json={"name": "Rent", "flow": "in"}
        )

        assert response.status_code == 422
        assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_flow_only_body_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        created = _create(client, "Rent", "out")

        assert (
            client.patch(f"{PATH}/{created['id']}", json={"flow": "in"}).status_code
            == 422
        )

    def test_missing_name_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        created = _create(client, "Rent", "out")

        assert client.patch(f"{PATH}/{created['id']}", json={}).status_code == 422

    def test_overlong_name_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        created = _create(client, "Rent", "out")

        response = client.patch(f"{PATH}/{created['id']}", json={"name": "x" * 65})

        assert response.status_code == 422

    def test_unknown_id_returns_404(self, client: FlaskClient, as_alice: User) -> None:
        assert client.patch(f"{PATH}/999", json={"name": "Rent"}).status_code == 404

    def test_soft_deleted_concept_returns_410(
        self,
        client: FlaskClient,
        as_alice: User,
        make_concept: Callable[..., Concept],
    ) -> None:
        gone = make_concept("Gone", is_deleted=True)

        response = client.patch(f"{PATH}/{gone.id}", json={"name": "Back"})

        assert response.status_code == 410
        assert response.get_json()["error"] == {
            "code": "GONE",
            "message": "Record not available anymore.",
        }


class TestDeleteConcept:
    def test_soft_deletes(self, client: FlaskClient, as_alice: User) -> None:
        created = _create(client, "Rent", "out")

        response = client.delete(f"{PATH}/{created['id']}")

        assert response.status_code == 200
        assert response.get_json() == {"data": None, "error": None, "meta": None}
        stored = db.session.get(Concept, created["id"])
        assert stored is not None
        assert stored.is_deleted is True

    def test_deleted_concept_leaves_the_default_list(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        created = _create(client, "Rent", "out")

        client.delete(f"{PATH}/{created['id']}")

        assert client.get(PATH).get_json()["data"] == []

    def test_referencing_records_are_not_mutated(
        self,
        client: FlaskClient,
        as_alice: User,
        make_transaction: Callable[..., Transaction],
        make_budget: Callable[..., Budget],
    ) -> None:
        """BACKEND.md § 1.2: deleting a concept never cascades."""
        created = _create(client, "Rent", "out")
        concept = db.session.get(Concept, created["id"])
        assert concept is not None
        transaction = make_transaction(
            concept=concept, user=as_alice, amount="10.00", on=date(2025, 7, 1)
        )
        budget = make_budget(
            concept=concept, user=as_alice, amount="900.00", on=date(2025, 7, 1)
        )

        client.delete(f"{PATH}/{created['id']}")

        db.session.refresh(transaction)
        db.session.refresh(budget)
        assert transaction.is_deleted is False
        assert budget.is_deleted is False

    def test_unknown_id_returns_404(self, client: FlaskClient, as_alice: User) -> None:
        assert client.delete(f"{PATH}/999").status_code == 404

    def test_already_deleted_returns_410(
        self,
        client: FlaskClient,
        as_alice: User,
        make_concept: Callable[..., Concept],
    ) -> None:
        gone = make_concept("Gone", is_deleted=True)

        response = client.delete(f"{PATH}/{gone.id}")

        assert response.status_code == 410
        assert (
            response.get_json()["error"]["message"] == "Record not available anymore."
        )

    def test_any_user_may_delete(
        self,
        client: FlaskClient,
        as_alice: User,
        make_user: Callable[..., User],
    ) -> None:
        """FRONTEND.md: peers act by agreement; deletion is not admin-gated."""
        created = _create(client, "Rent", "out")

        assert client.delete(f"{PATH}/{created['id']}").status_code == 200


class TestBulkDeleteConcepts:
    def test_deletes_all_listed_ids(self, client: FlaskClient, as_alice: User) -> None:
        first = _create(client, "Rent", "out")
        second = _create(client, "Food", "out")

        response = client.delete(f"{PATH}?ids={first['id']},{second['id']}")

        assert response.status_code == 200
        assert response.get_json() == {
            "data": {"deleted": 2},
            "error": None,
            "meta": None,
        }
        assert client.get(PATH).get_json()["data"] == []

    def test_all_or_nothing_on_a_missing_id(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        first = _create(client, "Rent", "out")

        response = client.delete(f"{PATH}?ids={first['id']},999")

        assert response.status_code == 404
        assert client.get(PATH).get_json()["data"] != []

    def test_all_or_nothing_on_an_already_deleted_id(
        self,
        client: FlaskClient,
        as_alice: User,
        make_concept: Callable[..., Concept],
    ) -> None:
        first = _create(client, "Rent", "out")
        gone = make_concept("Gone", is_deleted=True)

        response = client.delete(f"{PATH}?ids={first['id']},{gone.id}")

        assert response.status_code == 410
        assert len(client.get(PATH).get_json()["data"]) == 1

    def test_missing_ids_returns_422(self, client: FlaskClient, as_alice: User) -> None:
        assert client.delete(PATH).status_code == 422

    def test_blank_ids_returns_422(self, client: FlaskClient, as_alice: User) -> None:
        assert client.delete(f"{PATH}?ids=").status_code == 422

    def test_malformed_ids_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        assert client.delete(f"{PATH}?ids=1,abc").status_code == 422

    def test_more_than_one_hundred_ids_returns_422(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        ids = ",".join(str(i) for i in range(1, 102))

        assert client.delete(f"{PATH}?ids={ids}").status_code == 422

    def test_exactly_one_hundred_ids_is_accepted(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        """The cap is on the id count, not on the rows existing."""
        ids = ",".join(str(i) for i in range(1, 101))

        assert client.delete(f"{PATH}?ids={ids}").status_code == 404

    def test_duplicate_ids_are_collapsed(
        self, client: FlaskClient, as_alice: User
    ) -> None:
        first = _create(client, "Rent", "out")

        response = client.delete(f"{PATH}?ids={first['id']},{first['id']}")

        assert response.get_json()["data"] == {"deleted": 1}
