"""`/history` (API_SURFACE.md § 9, BACKEND.md § 4.6)."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import add_budget, add_member, insert_transaction


@pytest.fixture
def ledger(admin: TestClient, db: Session) -> dict[str, dict[str, object]]:
    """August and July with a mix of budgets, one deleted budget and one deleted row."""
    groceries = add_budget(admin, "Groceries")
    dining = add_budget(admin, "Dining out")
    paycheck = add_budget(admin, "Paycheck")
    gone = add_budget(admin, "Old fun")
    rows = [
        (groceries, -21240, date(2026, 8, 24), "Greenfield Market"),
        (dining, -8800, date(2026, 8, 21), "Kiez Bistro"),
        (paycheck, 224000, date(2026, 8, 29), "Paycheck Northwind"),
        (gone, -4200, date(2026, 8, 15), "Cinema"),
        (groceries, -30175, date(2026, 7, 22), "Greenfield Market"),
        (groceries, -999, date(2026, 9, 2), "September is not history"),
    ]
    for budget, amount, day, payee in rows:
        insert_transaction(db, str(budget["id"]), amount, day, payee=payee)
    insert_transaction(db, str(dining["id"]), -100, date(2026, 8, 1), deleted=True)
    admin.delete(f"/api/v1/budgets/{gone['id']}")
    return {
        "groceries": groceries,
        "dining": dining,
        "paycheck": paycheck,
        "gone": gone,
    }


def test_months_list_past_months_newest_first(
    admin: TestClient, ledger: dict[str, dict[str, object]]
) -> None:
    body = admin.get("/api/v1/history/months").json()
    assert body["total"] == 2
    august, july = body["items"]
    assert august == {
        "month": "2026-08",
        "matchCount": 4,
        "totalCount": 4,
        "spent": 30040,
        "earned": 224000,
    }
    assert july["month"] == "2026-07"
    assert july["spent"] == 30175


def test_months_filtered_by_search_only_keep_matches(
    admin: TestClient, ledger: dict[str, dict[str, object]]
) -> None:
    body = admin.get("/api/v1/history/months?q=greenFIELD").json()
    assert [(m["month"], m["matchCount"], m["totalCount"]) for m in body["items"]] == [
        ("2026-08", 1, 4),
        ("2026-07", 1, 1),
    ]
    assert body["items"][0]["spent"] == 21240
    assert body["items"][0]["earned"] == 0


def test_months_search_matches_category_and_member(
    admin: TestClient, ledger: dict[str, dict[str, object]]
) -> None:
    by_category = admin.get("/api/v1/history/months?q=dining").json()["items"]
    assert [m["matchCount"] for m in by_category] == [1]
    by_member = admin.get("/api/v1/history/months?q=administ").json()["items"]
    assert sum(m["matchCount"] for m in by_member) == 5


def test_months_search_wildcards_are_literal(
    admin: TestClient, ledger: dict[str, dict[str, object]]
) -> None:
    assert admin.get("/api/v1/history/months?q=%25").json()["items"] == []
    assert admin.get("/api/v1/history/months?q=_").json()["items"] == []


def test_months_filtered_by_budget_and_member(
    admin: TestClient, ledger: dict[str, dict[str, object]]
) -> None:
    dining = ledger["dining"]["id"]
    body = admin.get(f"/api/v1/history/months?budgetId={dining}").json()
    assert [(m["month"], m["spent"]) for m in body["items"]] == [("2026-08", 8800)]
    jordan = add_member(admin, "jordan")
    nobody = admin.get(f"/api/v1/history/months?memberId={jordan['id']}").json()
    assert nobody == {"items": [], "page": 1, "size": 50, "total": 0}


def test_months_page(admin: TestClient, ledger: dict[str, dict[str, object]]) -> None:
    body = admin.get("/api/v1/history/months?page=2&size=1").json()
    assert [m["month"] for m in body["items"]] == ["2026-07"]
    assert body["total"] == 2


def test_month_transactions_include_deleted_categories(
    admin: TestClient, ledger: dict[str, dict[str, object]]
) -> None:
    body = admin.get("/api/v1/history/months/2026-08/transactions").json()
    assert [t["payee"] for t in body["items"]] == [
        "Paycheck Northwind",
        "Greenfield Market",
        "Kiez Bistro",
        "Cinema",
    ]
    assert body["total"] == 4
    cinema = body["items"][-1]
    assert cinema["categoryDeleted"] is True
    assert cinema["archived"] is True


def test_month_transactions_filtered(
    admin: TestClient, ledger: dict[str, dict[str, object]]
) -> None:
    body = admin.get("/api/v1/history/months/2026-08/transactions?q=kiez").json()
    assert [t["payee"] for t in body["items"]] == ["Kiez Bistro"]


@pytest.mark.parametrize("month", ["2026-09", "2026-10", "2026-13", "nope"])
def test_month_transactions_of_a_non_past_month_returns_404(
    admin: TestClient, month: str
) -> None:
    response = admin.get(f"/api/v1/history/months/{month}/transactions")
    assert response.status_code == 404


def test_breakdown_lists_counted_spending_by_category(
    admin: TestClient, ledger: dict[str, dict[str, object]]
) -> None:
    body = admin.get("/api/v1/history/months/2026-08/breakdown").json()
    assert body == {
        "month": "2026-08",
        "spent": 30040,
        "earned": 224000,
        "slices": [
            {
                "budgetId": ledger["groceries"]["id"],
                "category": "Groceries",
                "amount": 21240,
                "pct": 71,
            },
            {
                "budgetId": ledger["dining"]["id"],
                "category": "Dining out",
                "amount": 8800,
                "pct": 29,
            },
        ],
    }


def test_breakdown_respects_filters(
    admin: TestClient, ledger: dict[str, dict[str, object]]
) -> None:
    body = admin.get("/api/v1/history/months/2026-08/breakdown?q=kiez").json()
    assert (body["spent"], len(body["slices"])) == (8800, 1)


def test_breakdown_of_an_empty_past_month(admin: TestClient) -> None:
    body = admin.get("/api/v1/history/months/2026-01/breakdown").json()
    assert body == {"month": "2026-01", "spent": 0, "earned": 0, "slices": []}


def test_breakdown_of_current_month_returns_404(admin: TestClient) -> None:
    assert admin.get("/api/v1/history/months/2026-09/breakdown").status_code == 404


def test_facets_list_categories_and_members_of_past_months(
    admin: TestClient, ledger: dict[str, dict[str, object]]
) -> None:
    add_member(admin, "jordan")
    body = admin.get("/api/v1/history/facets").json()
    assert body["categories"] == [
        {"budgetId": ledger["groceries"]["id"], "name": "Groceries", "deleted": False},
        {"budgetId": ledger["dining"]["id"], "name": "Dining out", "deleted": False},
        {"budgetId": ledger["paycheck"]["id"], "name": "Paycheck", "deleted": False},
        {"budgetId": ledger["gone"]["id"], "name": "Old fun", "deleted": True},
    ]
    assert [m["username"] for m in body["members"]] == ["admin"]


def test_history_with_bad_filters_returns_400(admin: TestClient) -> None:
    response = admin.get("/api/v1/history/months?memberId=not-a-uuid")
    assert response.status_code == 400


def test_history_without_session_returns_401(client: TestClient) -> None:
    assert client.get("/api/v1/history/months").status_code == 401
