"""Auth endpoints and the forced password change (API_SURFACE.md § 2)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.adapters.security import Argon2Hasher
from app.config import Settings
from app.domain.entities import LoginSession, Member
from app.main import create_app
from tests.conftest import seed_database
from tests.helpers import JSON, FakeClock, sign_in


def test_login_with_valid_credentials_returns_session_and_cookie(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mustChangePassword"] is True
    assert body["member"]["username"] == "admin"
    assert body["member"]["realName"] == "Administrador"
    assert body["member"]["role"] == "admin"
    assert body["member"]["initial"] == "A"
    assert body["member"]["spentThisMonth"] == 0
    assert body["preferences"] == {"language": None, "theme": "system"}
    cookie = response.headers["set-cookie"].lower()
    assert "venn_session=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "secure" not in cookie


def test_login_stores_only_a_token_hash(client: TestClient, db: Session) -> None:
    client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    token = client.cookies["venn_session"]
    stored = db.scalars(select(LoginSession)).one()
    assert stored.token_hash != token
    assert len(stored.token_hash) == 64


def test_login_with_wrong_password_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "wrong-pass"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_login_with_unknown_user_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"username": "ghost", "password": "whatever"}
    )
    assert response.status_code == 401


def test_login_as_removed_member_returns_401(client: TestClient, db: Session) -> None:
    admin = db.scalars(select(Member)).one()
    admin.is_removed = True
    db.commit()
    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin"}
    )
    assert response.status_code == 401


def test_login_does_not_bump_revision(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin"}
    )
    assert response.headers["X-Ledger-Rev"] == "1"


def test_session_without_cookie_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/auth/session")
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_session_with_unknown_cookie_returns_401(client: TestClient) -> None:
    client.cookies.set("venn_session", "forged")
    assert client.get("/api/v1/auth/session").status_code == 401


def test_session_while_password_change_required_returns_403(
    client: TestClient,
) -> None:
    client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    response = client.get("/api/v1/auth/session")
    assert response.status_code == 403
    assert response.json()["code"] == "PASSWORD_CHANGE_REQUIRED"


def test_change_password_with_correct_current_lifts_gate(client: TestClient) -> None:
    client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    response = client.post(
        "/api/v1/auth/password",
        json={"currentPassword": "admin", "newPassword": "a-new-password"},
    )
    assert response.status_code == 204
    session = client.get("/api/v1/auth/session")
    assert session.status_code == 200
    assert session.json()["mustChangePassword"] is False


def test_change_password_to_the_same_value_lifts_gate(client: TestClient) -> None:
    client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    client.post(
        "/api/v1/auth/password",
        json={"currentPassword": "admin", "newPassword": "admin-pass"},
    )
    response = client.post(
        "/api/v1/auth/password",
        json={"currentPassword": "admin-pass", "newPassword": "admin-pass"},
    )
    assert response.status_code == 204


def test_change_password_with_wrong_current_returns_400(client: TestClient) -> None:
    client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    response = client.post(
        "/api/v1/auth/password",
        json={"currentPassword": "nope-nope", "newPassword": "a-new-password"},
    )
    assert response.status_code == 400
    assert response.json()["field"] == "currentPassword"


def test_change_password_too_short_returns_400(client: TestClient) -> None:
    client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    response = client.post(
        "/api/v1/auth/password",
        json={"currentPassword": "admin", "newPassword": "short"},
    )
    assert response.status_code == 400
    assert response.json()["field"] == "newPassword"


def test_change_password_keeps_current_session_and_drops_others(
    client: TestClient, db: Session
) -> None:
    client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    other = TestClient(client.app)
    other.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    client.post(
        "/api/v1/auth/password",
        json={"currentPassword": "admin", "newPassword": "a-new-password"},
    )
    assert client.get("/api/v1/auth/session").status_code == 200
    assert other.get("/api/v1/auth/session").status_code == 401
    assert db.scalar(select(func.count()).select_from(LoginSession)) == 1


def test_logout_deletes_session_and_clears_cookie(
    client: TestClient, db: Session
) -> None:
    sign_in(client)
    response = client.post("/api/v1/auth/logout", headers=JSON)
    assert response.status_code == 204
    assert db.scalar(select(func.count()).select_from(LoginSession)) == 0
    assert client.get("/api/v1/auth/session").status_code == 401


def test_logout_while_password_change_required_returns_204(
    client: TestClient,
) -> None:
    client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert client.post("/api/v1/auth/logout", headers=JSON).status_code == 204


def test_logout_without_session_returns_401(client: TestClient) -> None:
    assert client.post("/api/v1/auth/logout", headers=JSON).status_code == 401


def test_login_in_production_sets_secure_cookie(
    engine: Engine, clock: FakeClock, hasher: Argon2Hasher
) -> None:
    settings = Settings(database_url="sqlite://", app_env="production")
    seed_database(engine, settings, hasher, clock)
    app = create_app(settings, engine=engine, clock=clock, hasher=hasher)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "admin"}
        )
    assert "secure" in response.headers["set-cookie"].lower()
