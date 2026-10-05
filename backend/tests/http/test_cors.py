"""Cross-origin calls from the frontend's own port (CORS_ORIGINS)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.adapters.security import Argon2Hasher
from app.config import Settings, settings_from_env
from app.main import create_app
from tests.conftest import seed_database
from tests.helpers import FakeClock

FRONTEND = "http://venn-manager.kosumo"


@pytest.fixture
def cors(
    engine: Engine, clock: FakeClock, hasher: Argon2Hasher
) -> Iterator[TestClient]:
    settings = Settings(database_url="sqlite://", cors_origins=(FRONTEND,))
    seed_database(engine, settings, hasher, clock)
    with TestClient(
        create_app(settings, engine=engine, clock=clock, hasher=hasher)
    ) as client:
        yield client


def test_preflight_from_the_frontend_is_allowed_with_credentials(
    cors: TestClient,
) -> None:
    response = cors.options(
        "/api/v1/auth/login",
        headers={
            "Origin": FRONTEND,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND
    assert response.headers["access-control-allow-credentials"] == "true"


def test_responses_expose_the_revision_header(cors: TestClient) -> None:
    response = cors.get("/api/v1/auth/session", headers={"Origin": FRONTEND})
    assert response.headers["access-control-allow-origin"] == FRONTEND
    assert "X-Ledger-Rev" in response.headers["access-control-expose-headers"]


def test_other_origins_get_no_cors_headers(cors: TestClient) -> None:
    response = cors.get("/api/v1/auth/session", headers={"Origin": "http://evil.test"})
    assert "access-control-allow-origin" not in response.headers


def test_without_origins_no_cors_headers_are_sent(client: TestClient) -> None:
    response = client.get("/api/v1/auth/session", headers={"Origin": FRONTEND})
    assert "access-control-allow-origin" not in response.headers


def test_settings_read_a_comma_separated_origin_list() -> None:
    settings = settings_from_env({"CORS_ORIGINS": " http://a , http://b:80 ,"})
    assert settings.cors_origins == ("http://a", "http://b:80")
    assert settings_from_env({}).cors_origins == ()
