"""`/balance` (API_SURFACE.md § 10, BACKEND.md § 4.5)."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import add_budget, add_member, insert_transaction, sign_in


def test_balance_adds_opening_earlier_and_current(
    admin: TestClient, db: Session
) -> None:
    admin.patch("/api/v1/household", json={"openingBalance": 50000})
    budget = add_budget(admin, "Groceries")
    insert_transaction(db, str(budget["id"]), -10000, date(2026, 8, 3))
    insert_transaction(db, str(budget["id"]), 30000, date(2026, 9, 3))
    insert_transaction(db, str(budget["id"]), -5000, date(2026, 9, 4))
    body = admin.get("/api/v1/balance").json()
    assert body == {
        "balance": 65000,
        "monthIn": 30000,
        "monthOut": 5000,
        "members": None,
    }


def test_balance_lists_member_income_when_enabled(
    admin: TestClient, other: TestClient, db: Session
) -> None:
    admin.patch("/api/v1/household", json={"showMemberIncome": True})
    budget = add_budget(admin, "Paycheck")
    jordan = add_member(admin, "jordan")
    sign_in(other, "jordan", "initial-pass")
    insert_transaction(db, str(budget["id"]), 100000, date(2026, 8, 3))
    other.post(
        "/api/v1/transactions",
        json={"budgetId": budget["id"], "amount": 224000},
    )
    admin.post(
        "/api/v1/transactions",
        json={"budgetId": budget["id"], "amount": 5000},
    )
    members = admin.get("/api/v1/balance").json()["members"]
    me = admin.get("/api/v1/auth/session").json()["member"]
    assert members == [
        {"memberId": jordan["id"], "monthIn": 224000, "allTimeIn": 224000},
        {"memberId": me["id"], "monthIn": 5000, "allTimeIn": 105000},
    ]


def test_balance_without_session_returns_401(client: TestClient) -> None:
    assert client.get("/api/v1/balance").status_code == 401
