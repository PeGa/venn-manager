"""Application factory, response envelope and error handling."""

from __future__ import annotations

import os
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app

TEST_SECRET_KEY = "pytest-only-secret-key-not-used-in-production"


def _sqlite_uri(tmp_path: os.PathLike[str]) -> str:
    return f"sqlite:///{os.path.join(str(tmp_path), 'factory.db')}"


class TestCreateApp:
    def test_missing_secret_key_is_refused(
        self, tmp_path: os.PathLike[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SECRET_KEY", raising=False)

        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            create_app({"SQLALCHEMY_DATABASE_URI": _sqlite_uri(tmp_path)})

    def test_empty_secret_key_is_refused(self, tmp_path: os.PathLike[str]) -> None:
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            create_app(
                {
                    "SECRET_KEY": "",
                    "SQLALCHEMY_DATABASE_URI": _sqlite_uri(tmp_path),
                }
            )

    def test_short_secret_key_is_refused(self, tmp_path: os.PathLike[str]) -> None:
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            create_app(
                {
                    "SECRET_KEY": "too-short",
                    "SQLALCHEMY_DATABASE_URI": _sqlite_uri(tmp_path),
                }
            )

    def test_development_disables_secure_cookie(self, app: Flask) -> None:
        assert app.config["SESSION_COOKIE_SECURE"] is False

    def test_production_enables_secure_cookie(self, tmp_path: os.PathLike[str]) -> None:
        application = create_app(
            {
                "SECRET_KEY": TEST_SECRET_KEY,
                "FLASK_ENV": "production",
                "SQLALCHEMY_DATABASE_URI": _sqlite_uri(tmp_path),
            }
        )

        assert application.config["SESSION_COOKIE_SECURE"] is True

    def test_session_cookie_flags(self, app: Flask) -> None:
        assert app.config["SESSION_COOKIE_HTTPONLY"] is True
        assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


class TestEnvelope:
    def test_unknown_route_returns_not_found_envelope(
        self, client: FlaskClient
    ) -> None:
        response = client.get("/api/v1/nope")

        assert response.status_code == 404
        assert response.content_type.startswith("application/json")
        assert response.get_json() == {
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "Resource not found"},
            "meta": None,
        }

    def test_unknown_method_is_reported_as_not_found(self, client: FlaskClient) -> None:
        # API_SURFACE.md lists no 405 code, so an unsupported method on a known
        # path is reported inside the documented status set as NOT_FOUND.
        response = client.delete("/api/v1/nope")

        assert response.status_code == 404
        assert response.get_json()["error"]["code"] == "NOT_FOUND"

    def test_unhandled_exception_is_sanitised(
        self, app: Flask, client: FlaskClient
    ) -> None:
        @app.route("/api/v1/_boom")
        def _boom() -> Any:
            raise RuntimeError("secret internal detail")

        response = client.get("/api/v1/_boom")

        assert response.status_code == 500
        assert response.get_json() == {
            "data": None,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
            },
            "meta": None,
        }
        assert b"secret internal detail" not in response.data
        assert b"Traceback" not in response.data

    def test_malformed_json_body_is_a_validation_error(
        self, app: Flask, client: FlaskClient
    ) -> None:
        @app.route("/api/v1/_echo", methods=["POST"])
        def _echo() -> Any:
            from flask import request

            return {"data": request.get_json(), "error": None, "meta": None}

        response = client.post(
            "/api/v1/_echo", data="{not json", content_type="application/json"
        )

        assert response.status_code == 422
        assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"
