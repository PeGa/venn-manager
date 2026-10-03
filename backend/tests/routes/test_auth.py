"""Endpoint tests for API_SURFACE.md § 1 (auth)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.models import User

PASSWORD = "secret-pass"


@pytest.fixture()
def alice(make_user: Callable[..., User]) -> User:
    return make_user("alice", password=PASSWORD, real_name="Alice Doe")


@pytest.fixture()
def root(make_user: Callable[..., User]) -> User:
    return make_user("root", password=PASSWORD, real_name="Root", is_admin=True)


def _login(client: FlaskClient, username: str, password: str) -> Any:
    return client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )


class TestLogin:
    def test_valid_credentials_return_200_with_user(
        self, client: FlaskClient, alice: User
    ) -> None:
        response = _login(client, "alice", PASSWORD)

        assert response.status_code == 200
        assert response.get_json() == {
            "data": {"user": _user_payload(alice), "must_change_password": False},
            "error": None,
            "meta": None,
        }

    def test_sets_a_session_cookie(self, client: FlaskClient, alice: User) -> None:
        _login(client, "alice", PASSWORD)

        cookie = client.get_cookie("session")

        assert cookie is not None
        # AGENTS.md § Authentication & Session Security. `secure` is False here
        # because the test app runs with FLASK_ENV=development.
        assert cookie.http_only is True
        assert cookie.same_site == "Lax"
        assert cookie.secure is False

    def test_unknown_username_returns_401(self, client: FlaskClient) -> None:
        response = _login(client, "nobody", PASSWORD)

        assert response.status_code == 401
        assert response.get_json() == {
            "data": None,
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Invalid username or password",
            },
            "meta": None,
        }

    def test_wrong_password_returns_401(self, client: FlaskClient, alice: User) -> None:
        assert _login(client, "alice", "wrong").status_code == 401

    def test_soft_deleted_user_returns_401(
        self, make_user: Callable[..., User], client: FlaskClient
    ) -> None:
        # API_SURFACE.md: a deleted user gets the same 401 as bad credentials,
        # so the response cannot be used to enumerate accounts.
        make_user("ghost", password=PASSWORD, is_deleted=True)

        response = _login(client, "ghost", PASSWORD)

        assert response.status_code == 401
        assert response.get_json()["error"]["message"] == "Invalid username or password"

    def test_missing_password_returns_422(
        self, client: FlaskClient, alice: User
    ) -> None:
        response = client.post("/api/v1/auth/login", json={"username": "alice"})

        assert response.status_code == 422
        assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_non_string_username_returns_422(self, client: FlaskClient) -> None:
        response = client.post(
            "/api/v1/auth/login", json={"username": 7, "password": PASSWORD}
        )

        assert response.status_code == 422

    def test_non_object_body_returns_422(self, client: FlaskClient) -> None:
        response = client.post("/api/v1/auth/login", json=["alice", PASSWORD])

        assert response.status_code == 422

    def test_whitespace_around_username_is_ignored(
        self, client: FlaskClient, alice: User
    ) -> None:
        assert _login(client, "  alice  ", PASSWORD).status_code == 200


class TestSession:
    def test_without_login_returns_401(self, client: FlaskClient) -> None:
        response = client.get("/api/v1/auth/session")

        assert response.status_code == 401
        assert response.get_json()["error"] == {
            "code": "UNAUTHORIZED",
            "message": "No active session",
        }

    def test_after_login_returns_the_same_shape_as_login(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice", PASSWORD)

        response = client.get("/api/v1/auth/session")

        assert response.status_code == 200
        assert response.get_json()["data"] == {
            "user": _user_payload(alice),
            "must_change_password": False,
        }


class TestLogout:
    def test_returns_200_and_ends_the_session(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice", PASSWORD)

        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 200
        assert response.get_json() == {"data": None, "error": None, "meta": None}
        assert client.get("/api/v1/auth/session").status_code == 401

    def test_without_login_returns_401(self, client: FlaskClient) -> None:
        assert client.post("/api/v1/auth/logout").status_code == 401

    def test_a_copied_cookie_stops_working(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        """AGENTS.md: logout must invalidate server-side, not just clear the cookie."""
        login("alice", PASSWORD)
        stolen = client.get_cookie("session")
        assert stolen is not None

        client.post("/api/v1/auth/logout")
        client.set_cookie("session", stolen.value)

        assert client.get("/api/v1/auth/session").status_code == 401

    def test_other_sessions_of_the_same_user_are_invalidated(
        self, app: Flask, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice", PASSWORD)
        stolen = client.get_cookie("session")
        assert stolen is not None

        other = app.test_client()
        other.set_cookie("session", stolen.value)
        assert other.get("/api/v1/auth/session").status_code == 200

        client.post("/api/v1/auth/logout")

        assert other.get("/api/v1/auth/session").status_code == 401


class TestPasswordChange:
    def test_successful_change_returns_200_null(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice", PASSWORD)

        response = client.post(
            "/api/v1/auth/password",
            json={"current_password": PASSWORD, "new_password": "a-new-password"},
        )

        assert response.status_code == 200
        assert response.get_json() == {"data": None, "error": None, "meta": None}

    def test_new_password_is_effective(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice", PASSWORD)
        client.post(
            "/api/v1/auth/password",
            json={"current_password": PASSWORD, "new_password": "a-new-password"},
        )
        client.post("/api/v1/auth/logout")

        assert _login(client, "alice", "a-new-password").status_code == 200
        assert _login(client, "alice", PASSWORD).status_code == 401

    def test_wrong_current_password_returns_401(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice", PASSWORD)

        response = client.post(
            "/api/v1/auth/password",
            json={"current_password": "nope", "new_password": "a-new-password"},
        )

        assert response.status_code == 401
        assert response.get_json()["error"]["code"] == "UNAUTHORIZED"

    def test_short_new_password_returns_422(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice", PASSWORD)

        response = client.post(
            "/api/v1/auth/password",
            json={"current_password": PASSWORD, "new_password": "short"},
        )

        assert response.status_code == 422
        assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_unchanged_password_returns_422(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice", PASSWORD)

        response = client.post(
            "/api/v1/auth/password",
            json={"current_password": PASSWORD, "new_password": PASSWORD},
        )

        assert response.status_code == 422

    def test_missing_fields_return_422(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice", PASSWORD)

        assert client.post("/api/v1/auth/password", json={}).status_code == 422

    def test_anonymous_request_returns_401(self, client: FlaskClient) -> None:
        response = client.post(
            "/api/v1/auth/password",
            json={"current_password": PASSWORD, "new_password": "a-new-password"},
        )

        assert response.status_code == 401

    def test_change_keeps_the_current_session_alive(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice", PASSWORD)

        client.post(
            "/api/v1/auth/password",
            json={"current_password": PASSWORD, "new_password": "a-new-password"},
        )

        assert client.get("/api/v1/auth/session").status_code == 200

    def test_change_invalidates_other_sessions(
        self, app: Flask, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice", PASSWORD)
        stolen = client.get_cookie("session")
        assert stolen is not None
        other = app.test_client()
        other.set_cookie("session", stolen.value)

        client.post(
            "/api/v1/auth/password",
            json={"current_password": PASSWORD, "new_password": "a-new-password"},
        )

        assert other.get("/api/v1/auth/session").status_code == 401


def _user_payload(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "is_admin": user.is_admin,
    }
