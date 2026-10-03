"""`/members` (API_SURFACE.md § 5, BACKEND.md § 8)."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities import Activity, LoginSession
from tests.helpers import add_member, sign_in


def test_create_member_returns_201_with_flag_set(
    admin: TestClient, other: TestClient
) -> None:
    body = add_member(admin, "jordan")
    assert body["username"] == "jordan"
    assert body["realName"] == "Jordan"
    assert body["role"] == "member"
    assert body["color"] == "#a9c7b6"
    login = other.post(
        "/api/v1/auth/login", json={"username": "jordan", "password": "initial-pass"}
    )
    assert login.json()["mustChangePassword"] is True
    assert login.json()["preferences"] == {"language": None, "theme": "system"}


def test_create_member_records_invite_activity(admin: TestClient, db: Session) -> None:
    body = add_member(admin, "jordan")
    entry = db.scalars(select(Activity)).one()
    assert entry.action == "member.invite"
    assert entry.params == {"name": "Jordan"}
    assert str(entry.target_id) == body["id"]


def test_create_member_with_taken_username_returns_409(admin: TestClient) -> None:
    response = admin.post(
        "/api/v1/members",
        json={
            "username": "admin",
            "realName": "A",
            "password": "12345678",
            "isAdmin": False,
        },
    )
    assert response.status_code == 409
    assert response.json()["field"] == "username"


def test_create_member_with_short_password_returns_400(admin: TestClient) -> None:
    response = admin.post(
        "/api/v1/members",
        json={"username": "x", "realName": "X", "password": "short", "isAdmin": False},
    )
    assert response.json()["field"] == "password"


def test_create_member_as_non_admin_returns_403(
    admin: TestClient, other: TestClient
) -> None:
    add_member(admin, "jordan")
    sign_in(other, "jordan", "initial-pass")
    response = other.post(
        "/api/v1/members",
        json={
            "username": "y",
            "realName": "Y",
            "password": "12345678",
            "isAdmin": False,
        },
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_update_member_changes_name_and_role(admin: TestClient) -> None:
    jordan = add_member(admin, "jordan")
    response = admin.patch(
        f"/api/v1/members/{jordan['id']}",
        json={"realName": "Jordan L", "isAdmin": True},
    )
    assert response.status_code == 200
    assert response.json()["realName"] == "Jordan L"
    assert response.json()["role"] == "admin"


def test_update_member_password_forces_change_and_ends_sessions(
    admin: TestClient, other: TestClient
) -> None:
    jordan = add_member(admin, "jordan")
    sign_in(other, "jordan", "initial-pass")
    admin.patch(f"/api/v1/members/{jordan['id']}", json={"password": "reset-pass"})
    assert other.get("/api/v1/auth/session").status_code == 401
    login = other.post(
        "/api/v1/auth/login", json={"username": "jordan", "password": "reset-pass"}
    )
    assert login.json()["mustChangePassword"] is True


def test_update_member_demoting_last_admin_returns_409(admin: TestClient) -> None:
    me = admin.get("/api/v1/auth/session").json()["member"]
    response = admin.patch(f"/api/v1/members/{me['id']}", json={"isAdmin": False})
    assert response.status_code == 409
    assert response.json()["code"] == "LAST_ADMIN"


def test_update_member_demoting_one_of_two_admins_returns_200(
    admin: TestClient,
) -> None:
    add_member(admin, "jordan", is_admin=True)
    me = admin.get("/api/v1/auth/session").json()["member"]
    response = admin.patch(f"/api/v1/members/{me['id']}", json={"isAdmin": False})
    assert response.json()["role"] == "member"


def test_update_member_records_activity(admin: TestClient, db: Session) -> None:
    jordan = add_member(admin, "jordan")
    admin.patch(f"/api/v1/members/{jordan['id']}", json={"realName": "Jo"})
    actions = [e.action for e in db.scalars(select(Activity))]
    assert actions == ["member.invite", "member.update"]


def test_update_unknown_member_returns_404(admin: TestClient) -> None:
    response = admin.patch(
        "/api/v1/members/00000000-0000-4000-8000-000000000000", json={"realName": "X"}
    )
    assert response.status_code == 404


def test_update_removed_member_returns_410(admin: TestClient) -> None:
    jordan = add_member(admin, "jordan")
    admin.delete(f"/api/v1/members/{jordan['id']}")
    response = admin.patch(f"/api/v1/members/{jordan['id']}", json={"realName": "X"})
    assert response.status_code == 410


def test_update_member_with_empty_body_returns_400(admin: TestClient) -> None:
    jordan = add_member(admin, "jordan")
    assert admin.patch(f"/api/v1/members/{jordan['id']}", json={}).status_code == 400


def test_remove_member_ends_sessions_and_blocks_login(
    admin: TestClient, other: TestClient, db: Session
) -> None:
    jordan = add_member(admin, "jordan")
    sign_in(other, "jordan", "initial-pass")
    response = admin.delete(f"/api/v1/members/{jordan['id']}")
    assert response.status_code == 204
    assert other.get("/api/v1/auth/session").status_code == 401
    login = other.post(
        "/api/v1/auth/login",
        json={"username": "jordan", "password": "admin-password"},
    )
    assert login.status_code == 401
    assert db.scalar(select(func.count()).select_from(LoginSession)) == 1


def test_remove_member_keeps_username_reserved(admin: TestClient) -> None:
    jordan = add_member(admin, "jordan")
    admin.delete(f"/api/v1/members/{jordan['id']}")
    response = admin.post(
        "/api/v1/members",
        json={
            "username": "jordan",
            "realName": "J",
            "password": "12345678",
            "isAdmin": False,
        },
    )
    assert response.status_code == 409


def test_remove_member_records_activity(admin: TestClient, db: Session) -> None:
    jordan = add_member(admin, "jordan")
    admin.delete(f"/api/v1/members/{jordan['id']}")
    entry = list(db.scalars(select(Activity)))[-1]
    assert (entry.action, entry.params) == ("member.remove", {"name": "Jordan"})


def test_remove_self_returns_409(admin: TestClient) -> None:
    me = admin.get("/api/v1/auth/session").json()["member"]
    response = admin.delete(f"/api/v1/members/{me['id']}")
    assert response.status_code == 409
    assert response.json()["code"] == "SELF_REMOVAL"


def test_remove_member_twice_returns_410(admin: TestClient) -> None:
    jordan = add_member(admin, "jordan")
    admin.delete(f"/api/v1/members/{jordan['id']}")
    assert admin.delete(f"/api/v1/members/{jordan['id']}").status_code == 410


def test_remove_unknown_member_returns_404(admin: TestClient) -> None:
    response = admin.delete("/api/v1/members/00000000-0000-4000-8000-000000000000")
    assert response.status_code == 404
