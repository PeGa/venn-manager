"""`/overview` and `/upcoming` (API_SURFACE.md § 8, BACKEND.md § 4.3–4.4, § 5)."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import add_budget, insert_transaction


def _log(client: TestClient, budget: dict[str, object], amount: int) -> None:
    response = client.post(
        "/api/v1/transactions",
        json={"payee": "x", "budgetId": budget["id"], "amount": amount},
    )
    assert response.status_code == 201


def _forecast(client: TestClient) -> tuple[int, int, int]:
    f = client.get("/api/v1/overview").json()["forecast"]
    return f["transactionsNet"], f["planned"], f["total"]


def test_overview_follows_the_worked_example(admin: TestClient) -> None:
    """BACKEND.md § 4.7 through the API, in cents."""
    paycheck = add_budget(admin, "Paycheck", 10000)
    groceries = add_budget(admin, "Groceries", -1000)
    add_budget(admin, "Car repair", -3000)
    add_budget(admin, "Rent", -2000)
    assert _forecast(admin) == (0, 4000, 4000)
    _log(admin, groceries, -500)
    assert _forecast(admin) == (-500, 4500, 4000)
    _log(admin, groceries, -2500)
    assert _forecast(admin) == (-3000, 5000, 2000)
    _log(admin, paycheck, 10000)
    assert _forecast(admin) == (7000, -5000, 2000)


def test_overview_start_cash_carries_earlier_months(
    admin: TestClient, db: Session
) -> None:
    admin.patch("/api/v1/household", json={"openingBalance": 100000})
    budget = add_budget(admin, "Groceries", -1000)
    insert_transaction(db, str(budget["id"]), -3000, date(2026, 8, 20))
    deleted = add_budget(admin, "Gone")
    insert_transaction(db, str(deleted["id"]), -50000, date(2026, 8, 20))
    admin.delete(f"/api/v1/budgets/{deleted['id']}")
    forecast = admin.get("/api/v1/overview").json()["forecast"]
    assert forecast["startCash"] == 97000
    assert forecast["transactionCount"] == 0


def test_overview_reports_budget_totals_and_period(admin: TestClient) -> None:
    groceries = add_budget(admin, "Groceries", -80000)
    goal = add_budget(admin, "Trip", -20000)
    admin.patch(f"/api/v1/budgets/{goal['id']}", json={"goal": True})
    _log(admin, groceries, -60000)
    body = admin.get("/api/v1/overview").json()
    assert body["period"]["month"] == "2026-09"
    assert body["currencySign"] == "$"
    assert body["budgetTotals"] == {
        "limit": 80000,
        "spent": 60000,
        "leftToSpend": 20000,
        "spentPct": 75.0,
    }


def test_overview_lists_latest_transactions_and_activity(admin: TestClient) -> None:
    budget = add_budget(admin, "Groceries")
    for amount in range(1, 7):
        _log(admin, budget, -amount)
    body = admin.get("/api/v1/overview").json()
    assert [t["amount"] for t in body["recentTransactions"]] == [-6, -5, -4, -3]
    assert len(body["activity"]) == 5
    assert body["activity"][0]["action"] == "tx.create"


def test_upcoming_lists_scheduled_budgets(admin: TestClient) -> None:
    rent = add_budget(admin, "Rent", -215000)
    internet = add_budget(admin, "Internet", -6500)
    admin.patch(
        f"/api/v1/budgets/{rent['id']}",
        json={"schedule": {"repeat": "monthly", "anchor": "2026-09-30"}},
    )
    admin.patch(
        f"/api/v1/budgets/{internet['id']}",
        json={"schedule": {"repeat": "once", "anchor": "2026-09-04"}},
    )
    items = admin.get("/api/v1/upcoming").json()
    assert items == [
        {
            "budgetId": internet["id"],
            "name": "Internet",
            "dueDate": "2026-09-04",
            "amount": -6500,
            "actual": 0,
            "soon": True,
            "overdue": True,
        },
        {
            "budgetId": rent["id"],
            "name": "Rent",
            "dueDate": "2026-09-30",
            "amount": -215000,
            "actual": 0,
            "soon": True,
            "overdue": False,
        },
    ]
    assert admin.get("/api/v1/overview").json()["upcoming"] == items


def test_upcoming_drops_paid_budgets(admin: TestClient) -> None:
    rent = add_budget(admin, "Rent", -215000)
    admin.patch(
        f"/api/v1/budgets/{rent['id']}",
        json={"schedule": {"repeat": "monthly", "anchor": "2026-09-30"}},
    )
    _log(admin, rent, -215000)
    assert admin.get("/api/v1/upcoming").json() == []


def test_overview_without_session_returns_401(client: TestClient) -> None:
    assert client.get("/api/v1/overview").status_code == 401
    assert client.get("/api/v1/upcoming").status_code == 401
