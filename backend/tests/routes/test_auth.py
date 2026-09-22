"""Tests for authentication routes.

Covers login, logout, session check (me), and password change flows.
"""

from werkzeug.security import generate_password_hash

from app import db
from app.models.user import User


class TestLogin:
    """POST /api/auth/login tests."""

    def test_login_with_valid_credentials_returns_200(self, client, admin_user):
        resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "testpass",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["user"]["username"] == "admin"
        assert data["user"]["must_change_password"] is False

    def test_login_with_invalid_password_returns_401(self, client, admin_user):
        resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong",
        })
        assert resp.status_code == 401

    def test_login_with_nonexistent_user_returns_401(self, client):
        resp = client.post("/api/auth/login", json={
            "username": "ghost", "password": "testpass",
        })
        assert resp.status_code == 401

    def test_login_with_missing_fields_returns_400(self, client):
        resp = client.post("/api/auth/login", json={"username": "admin"})
        assert resp.status_code == 400

    def test_login_with_must_change_password_returns_flag(self, client, db):
        user = User(
            username="newadmin", real_name="New", password_hash=generate_password_hash("pass"),
            is_admin=True, must_change_password=True,
        )
        db.session.add(user)
        db.session.commit()

        resp = client.post("/api/auth/login", json={
            "username": "newadmin", "password": "pass",
        })
        assert resp.status_code == 200
        assert resp.get_json()["user"]["must_change_password"] is True


class TestLogout:
    """POST /api/auth/logout tests."""

    def test_logout_with_valid_session_returns_200(self, auth_client):
        resp = auth_client.post("/api/auth/logout")
        assert resp.status_code == 200

    def test_logout_without_session_returns_401(self, client):
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 401


class TestMe:
    """GET /api/auth/me tests."""

    def test_me_returns_user_object(self, auth_client):
        resp = auth_client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.get_json()["user"]
        assert "password_hash" not in data
        assert "must_change_password" in data
        assert data["username"] == "admin"

    def test_me_without_session_returns_401(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401


class TestChangePassword:
    """POST /api/auth/change-password tests."""

    def test_change_password_with_correct_current_returns_200(self, auth_client, app):
        resp = auth_client.post("/api/auth/change-password", json={
            "current_password": "testpass", "new_password": "newpass123",
        })
        assert resp.status_code == 200

        with app.app_context():
            user = User.query.filter_by(username="admin").first()
            assert user.must_change_password is False

    def test_change_password_with_wrong_current_returns_401(self, auth_client):
        resp = auth_client.post("/api/auth/change-password", json={
            "current_password": "wrong", "new_password": "newpass123",
        })
        assert resp.status_code == 401

    def test_change_password_with_empty_new_returns_400(self, auth_client):
        resp = auth_client.post("/api/auth/change-password", json={
            "current_password": "testpass", "new_password": "",
        })
        assert resp.status_code == 400

    def test_change_password_clears_must_change_flag(self, client, db):
        user = User(
            username="forced", real_name="Forced", password_hash=generate_password_hash("old"),
            is_admin=True, must_change_password=True,
        )
        db.session.add(user)
        db.session.commit()

        client.post("/api/auth/login", json={"username": "forced", "password": "old"})
        resp = client.post("/api/auth/change-password", json={
            "current_password": "old", "new_password": "newpass",
        })
        assert resp.status_code == 200
        assert User.query.filter_by(username="forced").first().must_change_password is False
