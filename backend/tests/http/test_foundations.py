"""Error format, JSON guard and paging (API_SURFACE.md § 0, § 11)."""

from collections.abc import Iterator

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

from app.adapters.http.shapes import PageParams, page_params
from app.domain.errors import DomainError

probe = APIRouter(prefix="/api/v1/probe")


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: int


@probe.post("/echo")
def echo(body: Body) -> dict[str, int]:
    return {"amount": body.amount}


@probe.get("/conflict")
def conflict() -> None:
    raise DomainError("DUPLICATE_NAME", "Name already used", field="name")


@probe.get("/boom")
def boom() -> None:
    raise RuntimeError("secret internals /etc/passwd")


@probe.get("/page")
def page(params: PageParams = Depends(page_params)) -> dict[str, int]:
    return {"page": params.page, "size": params.size, "offset": params.offset}


@pytest.fixture
def probed(app: FastAPI) -> Iterator[TestClient]:
    app.include_router(probe)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_post_with_json_body_returns_200(probed: TestClient) -> None:
    response = probed.post("/api/v1/probe/echo", json={"amount": 5})
    assert response.status_code == 200
    assert response.json() == {"amount": 5}


def test_post_without_json_content_type_returns_400(probed: TestClient) -> None:
    response = probed.post("/api/v1/probe/echo", content="amount=5")
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION"


def test_post_with_wrong_type_returns_400_with_field(probed: TestClient) -> None:
    response = probed.post("/api/v1/probe/echo", json={"amount": "lots"})
    assert response.status_code == 400
    assert response.json() == {
        "code": "VALIDATION",
        "message": "Invalid amount",
        "field": "amount",
    }


def test_post_with_unknown_field_returns_400(probed: TestClient) -> None:
    response = probed.post("/api/v1/probe/echo", json={"amount": 1, "x": 2})
    assert response.status_code == 400
    assert response.json()["field"] == "x"


def test_post_with_malformed_json_returns_400_without_field(
    probed: TestClient,
) -> None:
    response = probed.post(
        "/api/v1/probe/echo",
        content="{",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert "field" not in response.json()


def test_app_error_returns_its_status_and_body(probed: TestClient) -> None:
    response = probed.get("/api/v1/probe/conflict")
    assert response.status_code == 409
    assert response.json() == {
        "code": "DUPLICATE_NAME",
        "message": "Name already used",
        "field": "name",
    }


def test_unhandled_exception_returns_generic_500(probed: TestClient) -> None:
    response = probed.get("/api/v1/probe/boom")
    assert response.status_code == 500
    assert response.json() == {"code": "INTERNAL", "message": "Unexpected error"}


def test_unknown_route_returns_404_not_found(probed: TestClient) -> None:
    response = probed.get("/api/v1/nowhere")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_unsupported_method_returns_404_not_found(probed: TestClient) -> None:
    response = probed.delete("/api/v1/probe/conflict")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_page_params_default_to_page_1_size_50(probed: TestClient) -> None:
    response = probed.get("/api/v1/probe/page")
    assert response.json() == {"page": 1, "size": 50, "offset": 0}


def test_page_params_compute_offset(probed: TestClient) -> None:
    response = probed.get("/api/v1/probe/page?page=3&size=20")
    assert response.json() == {"page": 3, "size": 20, "offset": 40}


@pytest.mark.parametrize("query", ["page=0", "size=0", "size=201", "page=x"])
def test_page_params_out_of_range_return_400(probed: TestClient, query: str) -> None:
    response = probed.get(f"/api/v1/probe/page?{query}")
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION"
