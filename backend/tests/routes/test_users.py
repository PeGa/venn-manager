"""Endpoint tests for API_SURFACE.md § 3.2 (user management)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.extensions import db
from app.models import Transaction, User

PATH = "/api/v1/settings/users"
PASSWORD = "secret-pass"


@pytest.fixture()
def root(make_user: Callable[..., User]) -> User:
    return make_user("root", real_name="Root Admin", is_admin=True)


@pytest.fixture()
def alice(make_user: Callable[..., User]) -> User:
    return make_user("alice", real_name="Alice Doe")


@pytest.fixture()
def as_root(client: FlaskClient, root: User, login: Callable[..., None]) -> User:
    login("root")
    return root


@pytest.fixture()
def as_alice(client: FlaskClient, alice: User, login: Callable[..., None]) -> User:
    login("alice")
    return alice


def _detail(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "is_admin": user.is_admin,
    }


class TestListUsers:
    def test_anonymous_returns_401(self, client: FlaskClient, root: User) -> None:
        assert client.get(PATH).status_code == 401

    def test_non_admin_returns_403(self, client: FlaskClient, as_alice: User) -> None:
        response = client.get(PATH)

        assert response.status_code == 403
        assert response.get_json()["error"]["code"] == "FORBIDDEN"

    def test_admin_gets_every_active_user(
        self, client: FlaskClient, as_root: User, alice: User
    ) -> None:
        response = client.get(PATH)

        assert response.status_code == 200
        assert response.get_json() == {
            "data": [_detail(as_root), _detail(alice)],
            "error": None,
            "meta": None,
        }

    def test_soft_deleted_users_are_excluded(
        self,
        client: FlaskClient,
        as_root: User,
        make_user: Callable[..., User],
    ) -> None:
        make_user("ghost", is_deleted=True)

        usernames = [u["username"] for u in client.get(PATH).get_json()["data"]]

        assert usernames == ["root"]

    def test_password_hashes_are_never_returned(
        self, client: FlaskClient, as_root: User
    ) -> None:
        body = client.get(PATH).data

        assert b"password" not in body
        assert b"scrypt" not in body

    def test_list_is_sorted_by_id(
        self,
        client: FlaskClient,
        as_root: User,
        make_user: Callable[..., User],
    ) -> None:
        make_user("carol")
        make_user("bob")

        ids = [u["id"] for u in client.get(PATH).get_json()["data"]]

        assert ids == sorted(ids)


class TestCreateUser:
    def test_admin_creates_a_user(self, client: FlaskClient, as_root: User) -> None:
        response = client.post(
            PATH,
            json={
                "username": "bob",
                "real_name": "Bob",
                "password": "a-strong-password",
                "is_admin": False,
            },
        )

        assert response.status_code == 201
        data = response.get_json()["data"]
        assert data["username"] == "bob"
        assert data["real_name"] == "Bob"
        assert data["is_admin"] is False
        assert "password" not in data
        assert client.get(PATH).get_json()["data"][-1]["username"] == "bob"

    def test_new_user_can_log_in(self, client: FlaskClient, as_root: User) -> None:
        client.post(
            PATH,
            json={
                "username": "bob",
                "real_name": "Bob",
                "password": "a-strong-password",
            },
        )
        client.post("/api/v1/auth/logout")

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "bob", "password": "a-strong-password"},
        )

        assert response.status_code == 200

    def test_is_admin_defaults_to_false(
        self, client: FlaskClient, as_root: User
    ) -> None:
        response = client.post(
            PATH,
            json={
                "username": "bob",
                "real_name": "Bob",
                "password": "a-strong-password",
            },
        )

        assert response.get_json()["data"]["is_admin"] is False

    def test_admin_flag_can_be_set(self, client: FlaskClient, as_root: User) -> None:
        response = client.post(
            PATH,
            json={
                "username": "bob",
                "real_name": "Bob",
                "password": "a-strong-password",
                "is_admin": True,
            },
        )

        assert response.get_json()["data"]["is_admin"] is True

    def test_non_admin_returns_403(self, client: FlaskClient, as_alice: User) -> None:
        response = client.post(
            PATH,
            json={
                "username": "bob",
                "real_name": "Bob",
                "password": "a-strong-password",
            },
        )

        assert response.status_code == 403

    def test_duplicate_username_returns_409(
        self, client: FlaskClient, as_root: User, alice: User
    ) -> None:
        response = client.post(
            PATH,
            json={
                "username": "alice",
                "real_name": "Other",
                "password": "a-strong-password",
            },
        )

        assert response.status_code == 409
        assert response.get_json()["error"]["code"] == "CONFLICT"

    def test_deleted_users_username_stays_reserved(
        self,
        client: FlaskClient,
        as_root: User,
        make_user: Callable[..., User],
    ) -> None:
        make_user("ghost", is_deleted=True)

        response = client.post(
            PATH,
            json={
                "username": "ghost",
                "real_name": "Ghost",
                "password": "a-strong-password",
            },
        )

        assert response.status_code == 409

    def test_missing_field_returns_422(
        self, client: FlaskClient, as_root: User
    ) -> None:
        response = client.post(PATH, json={"username": "bob", "real_name": "Bob"})

        assert response.status_code == 422
        assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_short_password_returns_422(
        self, client: FlaskClient, as_root: User
    ) -> None:
        response = client.post(
            PATH, json={"username": "bob", "real_name": "Bob", "password": "short"}
        )

        assert response.status_code == 422

    def test_overlong_username_returns_422(
        self, client: FlaskClient, as_root: User
    ) -> None:
        response = client.post(
            PATH,
            json={"username": "x" * 65, "real_name": "Bob", "password": PASSWORD},
        )

        assert response.status_code == 422

    def test_non_boolean_is_admin_returns_422(
        self, client: FlaskClient, as_root: User
    ) -> None:
        response = client.post(
            PATH,
            json={
                "username": "bob",
                "real_name": "Bob",
                "password": PASSWORD,
                "is_admin": "yes",
            },
        )

        assert response.status_code == 422

    def test_username_is_trimmed(self, client: FlaskClient, as_root: User) -> None:
        response = client.post(
            PATH,
            json={"username": "  bob  ", "real_name": "Bob", "password": PASSWORD},
        )

        assert response.get_json()["data"]["username"] == "bob"


class TestUpdateUser:
    def test_real_name_is_updated(
        self, client: FlaskClient, as_root: User, alice: User
    ) -> None:
        response = client.patch(f"{PATH}/{alice.id}", json={"real_name": "Alice Smith"})

        assert response.status_code == 200
        assert response.get_json()["data"]["real_name"] == "Alice Smith"

    def test_is_admin_can_be_granted(
        self, client: FlaskClient, as_root: User, alice: User
    ) -> None:
        response = client.patch(f"{PATH}/{alice.id}", json={"is_admin": True})

        assert response.get_json()["data"]["is_admin"] is True

    def test_password_can_be_reset(
        self, client: FlaskClient, as_root: User, alice: User
    ) -> None:
        client.patch(f"{PATH}/{alice.id}", json={"password": "a-brand-new-password"})
        client.post("/api/v1/auth/logout")

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "a-brand-new-password"},
        )

        assert response.status_code == 200

    def test_resetting_a_password_ends_their_sessions(
        self,
        app: Flask,
        client: FlaskClient,
        as_root: User,
        alice: User,
    ) -> None:
        victim = app.test_client()
        victim.post(
            "/api/v1/auth/login", json={"username": "alice", "password": PASSWORD}
        )
        assert victim.get("/api/v1/auth/session").status_code == 200

        client.patch(f"{PATH}/{alice.id}", json={"password": "a-brand-new-password"})

        assert victim.get("/api/v1/auth/session").status_code == 401

    def test_non_admin_returns_403(
        self, client: FlaskClient, as_alice: User, root: User
    ) -> None:
        assert (
            client.patch(f"{PATH}/{root.id}", json={"real_name": "Nope"}).status_code
            == 403
        )

    def test_unknown_id_returns_404(self, client: FlaskClient, as_root: User) -> None:
        assert (
            client.patch(f"{PATH}/999", json={"real_name": "Nobody"}).status_code == 404
        )

    def test_soft_deleted_user_returns_410(
        self,
        client: FlaskClient,
        as_root: User,
        make_user: Callable[..., User],
    ) -> None:
        ghost = make_user("ghost", is_deleted=True)

        response = client.patch(f"{PATH}/{ghost.id}", json={"real_name": "Nope"})

        assert response.status_code == 410
        assert response.get_json()["error"] == {
            "code": "GONE",
            "message": "Record not available anymore.",
        }

    def test_demoting_the_last_admin_returns_403(
        self, client: FlaskClient, as_root: User
    ) -> None:
        response = client.patch(f"{PATH}/{as_root.id}", json={"is_admin": False})

        assert response.status_code == 403
        assert response.get_json()["error"]["code"] == "FORBIDDEN"

    def test_demoting_an_admin_while_another_remains_is_allowed(
        self,
        client: FlaskClient,
        as_root: User,
        make_user: Callable[..., User],
    ) -> None:
        second = make_user("second", is_admin=True)

        response = client.patch(f"{PATH}/{second.id}", json={"is_admin": False})

        assert response.status_code == 200
        assert response.get_json()["data"]["is_admin"] is False

    def test_username_is_immutable(
        self, client: FlaskClient, as_root: User, alice: User
    ) -> None:
        response = client.patch(f"{PATH}/{alice.id}", json={"username": "alicia"})

        assert response.status_code == 422

    def test_short_password_returns_422(
        self, client: FlaskClient, as_root: User, alice: User
    ) -> None:
        assert (
            client.patch(f"{PATH}/{alice.id}", json={"password": "x"}).status_code
            == 422
        )

    def test_empty_body_returns_422(
        self, client: FlaskClient, as_root: User, alice: User
    ) -> None:
        assert client.patch(f"{PATH}/{alice.id}", json={}).status_code == 422

    def test_non_integer_id_returns_404(
        self, client: FlaskClient, as_root: User
    ) -> None:
        assert client.patch(f"{PATH}/abc", json={"real_name": "x"}).status_code == 404


class TestDeleteUser:
    def test_soft_deletes_the_user(
        self, client: FlaskClient, as_root: User, alice: User
    ) -> None:
        response = client.delete(f"{PATH}/{alice.id}")

        assert response.status_code == 200
        assert response.get_json() == {"data": None, "error": None, "meta": None}
        db.session.refresh(alice)
        assert alice.is_deleted is True

    def test_deleted_user_disappears_from_the_list(
        self, client: FlaskClient, as_root: User, alice: User
    ) -> None:
        client.delete(f"{PATH}/{alice.id}")

        usernames = [u["username"] for u in client.get(PATH).get_json()["data"]]

        assert usernames == ["root"]

    def test_deleted_user_cannot_log_in(
        self, client: FlaskClient, as_root: User, alice: User
    ) -> None:
        client.delete(f"{PATH}/{alice.id}")
        client.post("/api/v1/auth/logout")

        response = client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": PASSWORD}
        )

        assert response.status_code == 401

    def test_deleted_users_session_dies(
        self, app: Flask, client: FlaskClient, root: User, alice: User
    ) -> None:
        victim = app.test_client()
        victim.post(
            "/api/v1/auth/login", json={"username": "alice", "password": PASSWORD}
        )
        assert victim.get("/api/v1/auth/session").status_code == 200
        client.post(
            "/api/v1/auth/login", json={"username": "root", "password": PASSWORD}
        )

        client.delete(f"{PATH}/{alice.id}")

        assert victim.get("/api/v1/auth/session").status_code == 401

    def test_records_survive_with_their_user_id(
        self,
        client: FlaskClient,
        as_root: User,
        alice: User,
        make_concept: Callable[..., object],
        make_transaction: Callable[..., Transaction],
    ) -> None:
        concept = make_concept("Groceries", created_by=alice)
        transaction = make_transaction(
            concept=concept, user=alice, amount="10.00", on=date(2025, 7, 1)
        )

        client.delete(f"{PATH}/{alice.id}")

        stored = db.session.get(Transaction, transaction.id)
        assert stored is not None
        assert stored.user_id == alice.id
        assert stored.is_deleted is False

    def test_self_delete_returns_403(self, client: FlaskClient, as_root: User) -> None:
        response = client.delete(f"{PATH}/{as_root.id}")

        assert response.status_code == 403
        assert response.get_json()["error"]["code"] == "FORBIDDEN"

    def test_deleting_the_last_admin_returns_403(
        self, client: FlaskClient, as_root: User, alice: User
    ) -> None:
        response = client.delete(f"{PATH}/{as_root.id}")

        assert response.status_code == 403

    def test_deleting_a_second_admin_is_allowed(
        self,
        client: FlaskClient,
        as_root: User,
        make_user: Callable[..., User],
    ) -> None:
        second = make_user("second", is_admin=True)

        assert client.delete(f"{PATH}/{second.id}").status_code == 200

    def test_unknown_id_returns_404(self, client: FlaskClient, as_root: User) -> None:
        assert client.delete(f"{PATH}/999").status_code == 404

    def test_already_deleted_returns_410(
        self,
        client: FlaskClient,
        as_root: User,
        make_user: Callable[..., User],
    ) -> None:
        ghost = make_user("ghost", is_deleted=True)

        response = client.delete(f"{PATH}/{ghost.id}")

        assert response.status_code == 410
        assert (
            response.get_json()["error"]["message"] == "Record not available anymore."
        )

    def test_non_admin_returns_403(
        self, client: FlaskClient, as_alice: User, root: User
    ) -> None:
        assert client.delete(f"{PATH}/{root.id}").status_code == 403
