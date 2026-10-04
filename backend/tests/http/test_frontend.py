"""Serving the built frontend next to the API (API_SURFACE.md § 0: one origin)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.adapters.security import Argon2Hasher
from app.config import Settings
from app.main import create_app
from tests.conftest import seed_database
from tests.helpers import FakeClock


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    return tmp_path


@pytest.fixture
def served(
    dist: Path, engine: Engine, clock: FakeClock, hasher: Argon2Hasher
) -> Iterator[TestClient]:
    settings = Settings(database_url="sqlite://", frontend_dist=str(dist))
    seed_database(engine, settings, hasher, clock)
    app = create_app(settings, engine=engine, clock=clock, hasher=hasher)
    with TestClient(app) as client:
        yield client


def test_root_serves_the_app(served: TestClient) -> None:
    response = served.get("/")
    assert response.status_code == 200
    assert response.text == "<html>app</html>"


def test_screen_paths_fall_back_to_the_app(served: TestClient) -> None:
    for path in ("/budget", "/history", "/settings/anything"):
        assert served.get(path).text == "<html>app</html>"


def test_built_files_are_served(served: TestClient) -> None:
    assert served.get("/assets/app.js").text == "console.log(1)"
    assert served.get("/favicon.svg").text == "<svg/>"


def test_paths_outside_the_build_are_never_served(served: TestClient) -> None:
    response = served.get("/..%2F..%2Fetc%2Fpasswd")
    assert response.text == "<html>app</html>"


def test_unknown_api_paths_stay_contract_errors(served: TestClient) -> None:
    response = served.get("/api/v1/nowhere")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_api_still_answers(served: TestClient) -> None:
    assert served.get("/api/v1/auth/session").status_code == 401


def test_without_a_build_nothing_but_the_api_is_served(client: TestClient) -> None:
    assert client.get("/").status_code == 404
