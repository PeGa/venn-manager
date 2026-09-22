"""Tests for user management routes.

Covers admin-only CRUD, last-admin protection, permission checks.
"""

from app import db
from app.models.user import User


class TestListUsers:
    """GET /api/users tests."""

    def test_admin_can_list_users(self, auth_client):
        resp = auth_client.get("/api/users")
        assert resp.status_code == 200
        users = resp.get_json()["users"]
        assert len(users) >= 1

    def test_non_admin_gets_403(self, user_client):
        resp = user_client.get("/api/users")
        assert resp.status_code == 403

    def test_unauthenticated_gets_401(self, client):
        resp = client.get("/api/users")
        assert resp.status_code == 401


class TestCreateUser:
    """POST /api/users tests."""

    def test_admin_creates_user(self, auth_client):
        resp = auth_client.post("/api/users", json={
            "username": "newbie", "real_name": "New User",
            "password": "pass123", "is_admin": False,
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["username"] == "newbie"
        assert "password_hash" not in data

    def test_duplicate_username_returns_409(self, auth_client):
        auth_client.post("/api/users", json={
            "username": "dup", "real_name": "Dup", "password": "pass", "is_admin": False,
        })
        resp = auth_client.post("/api/users", json={
            "username": "dup", "real_name": "Dup2", "password": "pass", "is_admin": False,
        })
        assert resp.status_code == 409

    def test_non_admin_cannot_create(self, user_client):
        resp = user_client.post("/api/users", json={
            "username": "hack", "real_name": "Hax", "password": "pass", "is_admin": False,
        })
        assert resp.status_code == 403


class TestUpdateUser:
    """PUT /api/users/:id tests."""

    def test_admin_updates_user(self, auth_client, regular_user):
        resp = auth_client.put(f"/api/users/{regular_user.id}", json={
            "real_name": "Updated Name",
        })
        assert resp.status_code == 200
        assert resp.get_json()["real_name"] == "Updated Name"

    def test_update_nonexistent_returns_404(self, auth_client):
        resp = auth_client.put("/api/users/9999", json={"real_name": "Ghost"})
        assert resp.status_code == 404


class TestDeleteUser:
    """DELETE /api/users/:id tests."""

    def test_admin_deletes_regular_user(self, auth_client, regular_user):
        resp = auth_client.delete(f"/api/users/{regular_user.id}")
        assert resp.status_code == 200
        assert db.session.get(User, regular_user.id) is None

    def test_cannot_delete_last_admin(self, auth_client, admin_user):
        resp = auth_client.delete(f"/api/users/{admin_user.id}")
        assert resp.status_code == 400

    def test_delete_nonexistent_returns_404(self, auth_client):
        resp = auth_client.delete("/api/users/9999")
        assert resp.status_code == 404
