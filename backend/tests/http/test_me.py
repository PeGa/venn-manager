"""`PATCH /me` (API_SURFACE.md § 3)."""

from fastapi.testclient import TestClient

from tests.helpers import add_member


def test_patch_me_updates_profile_and_preferences(admin: TestClient) -> None:
    response = admin.patch(
        "/api/v1/me",
        json={
            "username": "alex",
            "realName": " Alex ",
            "language": "es",
            "theme": "dark",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["member"]["username"] == "alex"
    assert body["member"]["realName"] == "Alex"
    assert body["preferences"] == {"language": "es", "theme": "dark"}


def test_patch_me_bumps_revision(admin: TestClient) -> None:
    before = int(admin.get("/api/v1/auth/session").headers["X-Ledger-Rev"])
    response = admin.patch("/api/v1/me", json={"theme": "light"})
    assert int(response.headers["X-Ledger-Rev"]) == before + 1


def test_patch_me_with_taken_username_returns_409(admin: TestClient) -> None:
    add_member(admin, "jordan")
    response = admin.patch("/api/v1/me", json={"username": "jordan"})
    assert response.status_code == 409
    assert response.json() == {
        "code": "DUPLICATE_NAME",
        "message": "Username already used",
        "field": "username",
    }


def test_patch_me_with_own_username_returns_200(admin: TestClient) -> None:
    assert admin.patch("/api/v1/me", json={"username": "admin"}).status_code == 200


def test_patch_me_with_empty_body_returns_400(admin: TestClient) -> None:
    assert admin.patch("/api/v1/me", json={}).status_code == 400


def test_patch_me_with_null_field_returns_400(admin: TestClient) -> None:
    response = admin.patch("/api/v1/me", json={"realName": None})
    assert response.status_code == 400
    assert response.json()["field"] == "realName"


def test_patch_me_with_unknown_language_returns_400(admin: TestClient) -> None:
    response = admin.patch("/api/v1/me", json={"language": "fr"})
    assert response.json()["field"] == "language"


def test_patch_me_without_session_returns_401(client: TestClient) -> None:
    assert client.patch("/api/v1/me", json={"theme": "dark"}).status_code == 401
