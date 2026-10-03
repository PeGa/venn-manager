"""Auth gate tests: login_required, admin_required, force-password-change."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import select

from app.extensions import db
from app.models import Setting, User
from app.services.sessions import SESSION_EPOCH_KEY, bump_epoch
from tests.helpers import register_probe_routes

DEFAULT_PASSWORD = "admin"


@pytest.fixture()
def probes(app: Flask) -> None:
    register_probe_routes(app)


@pytest.fixture()
def alice(make_user: Callable[..., User]) -> User:
    return make_user("alice", password="secret-pass")


@pytest.fixture()
def root(make_user: Callable[..., User]) -> User:
    return make_user("root", password="secret-pass", is_admin=True)


@pytest.fixture()
def sole_default_admin(app: Flask) -> User:
    """A single user still on the seeded default password.

    This is the exact state API_SURFACE.md § Force Password Change keys on.
    """
    admin = User.create(
        username="admin",
        password=DEFAULT_PASSWORD,
        real_name="Administrator",
        is_admin=True,
    )
    db.session.add(admin)
    db.session.commit()
    return admin


def _login_as_default_admin(client: FlaskClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": DEFAULT_PASSWORD},
    )
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["data"]["must_change_password"] is True


class TestLoginRequired:
    def test_anonymous_request_returns_401_envelope(
        self, probes: None, client: FlaskClient
    ) -> None:
        response = client.get("/api/v1/_probe")

        assert response.status_code == 401
        assert response.get_json() == {
            "data": None,
            "error": {"code": "UNAUTHORIZED", "message": "No active session"},
            "meta": None,
        }

    def test_authenticated_request_passes(
        self,
        probes: None,
        client: FlaskClient,
        alice: User,
        login: Callable[..., None],
    ) -> None:
        login("alice")

        assert client.get("/api/v1/_probe").status_code == 200

    def test_probe_reports_the_calling_user(
        self, probes: None, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        body = client.get("/api/v1/_probe").get_json()

        assert body["data"] == {"username": "alice", "user_id": alice.id}


class TestAdminRequired:
    def test_anonymous_request_returns_401(
        self, probes: None, client: FlaskClient
    ) -> None:
        assert client.get("/api/v1/_admin").status_code == 401

    def test_non_admin_returns_403_forbidden(
        self,
        probes: None,
        client: FlaskClient,
        alice: User,
        login: Callable[..., None],
    ) -> None:
        login("alice")
        response = client.get("/api/v1/_admin")

        assert response.status_code == 403
        assert response.get_json()["error"]["code"] == "FORBIDDEN"

    def test_admin_passes(
        self, probes: None, client: FlaskClient, root: User, login: Callable[..., None]
    ) -> None:
        login("root")

        assert client.get("/api/v1/_admin").status_code == 200


class TestForcePasswordChangeGate:
    def test_other_endpoints_are_blocked(
        self,
        probes: None,
        client: FlaskClient,
        sole_default_admin: User,
    ) -> None:
        _login_as_default_admin(client)

        response = client.get("/api/v1/_probe")

        assert response.status_code == 403
        assert response.get_json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"

    def test_logout_is_permitted_during_force_change(
        self, client: FlaskClient, sole_default_admin: User
    ) -> None:
        # API_SURFACE.md § Force Password Change exempts logout, so a restricted
        # session can still end itself and let someone else sign in.
        _login_as_default_admin(client)

        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 200
        assert response.get_json() == {"data": None, "error": None, "meta": None}
        assert client.get("/api/v1/auth/session").status_code == 401

    def test_session_endpoint_is_blocked(
        self, client: FlaskClient, sole_default_admin: User
    ) -> None:
        _login_as_default_admin(client)

        assert client.get("/api/v1/auth/session").status_code == 403

    def test_password_endpoint_is_permitted(
        self, client: FlaskClient, sole_default_admin: User
    ) -> None:
        _login_as_default_admin(client)

        response = client.post(
            "/api/v1/auth/password",
            json={
                "current_password": DEFAULT_PASSWORD,
                "new_password": "a-real-password",
            },
        )

        assert response.status_code == 200, response.get_json()

    def test_gate_lifts_after_the_change(
        self,
        probes: None,
        client: FlaskClient,
        sole_default_admin: User,
    ) -> None:
        _login_as_default_admin(client)
        client.post(
            "/api/v1/auth/password",
            json={
                "current_password": DEFAULT_PASSWORD,
                "new_password": "a-real-password",
            },
        )

        assert client.get("/api/v1/_probe").status_code == 200
        assert client.get("/api/v1/auth/session").status_code == 200

    def test_gate_does_not_fire_with_two_users(
        self,
        probes: None,
        client: FlaskClient,
        alice: User,
        sole_default_admin: User,
    ) -> None:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": DEFAULT_PASSWORD},
        )

        assert login_response.status_code == 200
        assert login_response.get_json()["data"]["must_change_password"] is False
        assert client.get("/api/v1/_probe").status_code == 200

    def test_gate_does_not_fire_after_the_password_changed(
        self, client: FlaskClient, sole_default_admin: User
    ) -> None:
        sole_default_admin.set_password("a-real-password")
        db.session.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "a-real-password"},
        )

        assert response.get_json()["data"]["must_change_password"] is False


class TestSessionInvalidation:
    def test_soft_deleted_user_is_not_loaded(
        self,
        probes: None,
        client: FlaskClient,
        alice: User,
        login: Callable[..., None],
    ) -> None:
        login("alice")
        alice.is_deleted = True
        db.session.commit()

        assert client.get("/api/v1/_probe").status_code == 401

    def test_stale_epoch_is_rejected(
        self,
        probes: None,
        client: FlaskClient,
        alice: User,
        login: Callable[..., None],
    ) -> None:
        login("alice")
        bump_epoch(db.session, alice.id)
        db.session.commit()

        assert client.get("/api/v1/_probe").status_code == 401

    def test_bump_writes_a_per_user_setting_row(
        self, client: FlaskClient, alice: User, login: Callable[..., None]
    ) -> None:
        login("alice")

        client.post(
            "/api/v1/auth/password",
            json={"current_password": "secret-pass", "new_password": "a-new-password"},
        )

        row = db.session.scalar(
            select(Setting).where(
                Setting.key == SESSION_EPOCH_KEY, Setting.user_id == alice.id
            )
        )

        assert row is not None
        assert row.value == "1"
