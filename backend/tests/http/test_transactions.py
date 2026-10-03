"""`/transactions` (API_SURFACE.md § 7, BACKEND.md § 7)."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.persistence.tables import activity
from app.domain.entities import Activity
from tests.helpers import add_budget, add_member, insert_transaction, sign_in

UNKNOWN = "00000000-0000-4000-8000-000000000000"


def _actions(db: Session) -> list[tuple[str, dict[str, object]]]:
    entries = db.scalars(select(Activity).order_by(activity.c.at))
    return [(e.action, e.params) for e in entries]


def _add(
    client: TestClient, budget_id: object, amount: int = -2500, **extra: object
) -> dict[str, object]:
    response = client.post(
        "/api/v1/transactions",
        json={
            "payee": "Corner Coffee",
            "budgetId": budget_id,
            "amount": amount,
            **extra,
        },
    )
    assert response.status_code == 201, response.json()
    body: dict[str, object] = response.json()
    return body


def test_create_transaction_defaults_to_today_and_caller(admin: TestClient) -> None:
    budget = add_budget(admin, "Dining out", -35000)
    me = admin.get("/api/v1/auth/session").json()["member"]
    body = _add(admin, budget["id"])
    assert body["payee"] == "Corner Coffee"
    assert body["amount"] == -2500
    assert body["date"] == "2026-09-28"
    assert body["memberId"] == me["id"]
    assert body["category"] == "Dining out"
    assert body["categoryDeleted"] is False
    assert body["archived"] is False


def test_create_transaction_keeps_the_sign_as_sent(admin: TestClient) -> None:
    budget = add_budget(admin, "Paycheck", 224000)
    assert _add(admin, budget["id"], amount=-1000)["amount"] == -1000
    assert _add(admin, budget["id"], amount=1000)["amount"] == 1000


def test_create_transaction_records_activity(admin: TestClient, db: Session) -> None:
    budget = add_budget(admin, "Dining out")
    _add(admin, budget["id"])
    assert _actions(db)[-1] == ("tx.create", {"payee": "Corner Coffee"})


def test_create_transaction_for_another_member(admin: TestClient) -> None:
    budget = add_budget(admin, "Dining out")
    jordan = add_member(admin, "jordan")
    assert _add(admin, budget["id"], memberId=jordan["id"])["memberId"] == jordan["id"]


def test_create_transaction_for_removed_member_returns_400(admin: TestClient) -> None:
    budget = add_budget(admin, "Dining out")
    jordan = add_member(admin, "jordan")
    admin.delete(f"/api/v1/members/{jordan['id']}")
    response = admin.post(
        "/api/v1/transactions",
        json={
            "payee": "X",
            "budgetId": budget["id"],
            "amount": -1,
            "memberId": jordan["id"],
        },
    )
    assert response.status_code == 400
    assert response.json()["field"] == "memberId"


def test_create_transaction_with_zero_amount_returns_400(admin: TestClient) -> None:
    budget = add_budget(admin, "Dining out")
    response = admin.post(
        "/api/v1/transactions",
        json={"payee": "X", "budgetId": budget["id"], "amount": 0},
    )
    assert response.json()["field"] == "amount"


def test_create_transaction_outside_the_period_returns_400(admin: TestClient) -> None:
    budget = add_budget(admin, "Dining out")
    for day in ("2026-08-31", "2026-10-01"):
        response = admin.post(
            "/api/v1/transactions",
            json={"payee": "X", "budgetId": budget["id"], "amount": -1, "date": day},
        )
        assert response.status_code == 400
        assert response.json() == {
            "code": "OUT_OF_PERIOD",
            "message": "Date outside the current month",
            "field": "date",
        }


def test_create_transaction_on_a_future_day_of_the_period_returns_201(
    admin: TestClient,
) -> None:
    budget = add_budget(admin, "Rent")
    assert _add(admin, budget["id"], date="2026-09-30")["date"] == "2026-09-30"


def test_create_transaction_with_unknown_budget_returns_400(admin: TestClient) -> None:
    response = admin.post(
        "/api/v1/transactions", json={"payee": "X", "budgetId": UNKNOWN, "amount": -1}
    )
    assert response.json()["field"] == "budgetId"


def test_create_transaction_with_deleted_budget_returns_410(admin: TestClient) -> None:
    budget = add_budget(admin, "Rent")
    admin.delete(f"/api/v1/budgets/{budget['id']}")
    response = admin.post(
        "/api/v1/transactions",
        json={"payee": "X", "budgetId": budget["id"], "amount": -1},
    )
    assert response.status_code == 410


def test_create_transaction_with_blank_payee_returns_400(admin: TestClient) -> None:
    budget = add_budget(admin, "Rent")
    response = admin.post(
        "/api/v1/transactions",
        json={"payee": " ", "budgetId": budget["id"], "amount": -1},
    )
    assert response.json()["field"] == "payee"


def test_list_transactions_returns_current_period_newest_first(
    admin: TestClient, db: Session
) -> None:
    budget = add_budget(admin, "Groceries")
    insert_transaction(db, str(budget["id"]), -100, date(2026, 9, 2), payee="old")
    insert_transaction(db, str(budget["id"]), -100, date(2026, 8, 30), payee="august")
    insert_transaction(
        db, str(budget["id"]), -100, date(2026, 9, 2), payee="deleted", deleted=True
    )
    _add(admin, budget["id"])
    body = admin.get("/api/v1/transactions").json()
    assert [t["payee"] for t in body["items"]] == ["Corner Coffee", "old"]
    assert (body["page"], body["size"], body["total"]) == (1, 50, 2)


def test_list_transactions_pages(admin: TestClient, db: Session) -> None:
    budget = add_budget(admin, "Groceries")
    for day in range(1, 6):
        insert_transaction(
            db, str(budget["id"]), -100, date(2026, 9, day), payee=str(day)
        )
    body = admin.get("/api/v1/transactions?page=2&size=2").json()
    assert [t["payee"] for t in body["items"]] == ["3", "2"]
    assert body["total"] == 5


def test_list_transactions_includes_rows_of_deleted_budgets(
    admin: TestClient, db: Session
) -> None:
    budget = add_budget(admin, "Fun")
    _add(admin, budget["id"])
    admin.delete(f"/api/v1/budgets/{budget['id']}")
    item = admin.get("/api/v1/transactions").json()["items"][0]
    assert item["category"] == "Fun"
    assert item["categoryDeleted"] is True


def test_update_transaction_changes_fields(admin: TestClient, db: Session) -> None:
    dining = add_budget(admin, "Dining out")
    fun = add_budget(admin, "Fun")
    created = _add(admin, dining["id"])
    response = admin.patch(
        f"/api/v1/transactions/{created['id']}",
        json={
            "payee": "Cinema",
            "amount": -4200,
            "budgetId": fun["id"],
            "date": "2026-09-27",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["payee"], body["amount"], body["category"], body["date"]) == (
        "Cinema",
        -4200,
        "Fun",
        "2026-09-27",
    )
    assert body["updatedAt"] > body["createdAt"]
    assert _actions(db)[-1] == ("tx.update", {"payee": "Cinema"})


def test_update_transaction_twice_merges_activity(
    admin: TestClient, db: Session
) -> None:
    budget = add_budget(admin, "Dining out")
    created = _add(admin, budget["id"])
    admin.patch(f"/api/v1/transactions/{created['id']}", json={"amount": -1})
    admin.patch(f"/api/v1/transactions/{created['id']}", json={"amount": -2})
    assert [a for a, _ in _actions(db)].count("tx.update") == 1


def test_update_archived_transaction_returns_409(
    admin: TestClient, db: Session
) -> None:
    budget = add_budget(admin, "Groceries")
    old = insert_transaction(db, str(budget["id"]), -100, date(2026, 8, 30))
    response = admin.patch(f"/api/v1/transactions/{old.id}", json={"amount": -1})
    assert response.status_code == 409
    assert response.json()["code"] == "READ_ONLY_HISTORY"


def test_update_transaction_of_deleted_budget_returns_409(admin: TestClient) -> None:
    budget = add_budget(admin, "Fun")
    created = _add(admin, budget["id"])
    admin.delete(f"/api/v1/budgets/{budget['id']}")
    response = admin.patch(f"/api/v1/transactions/{created['id']}", json={"amount": -1})
    assert response.json()["code"] == "CATEGORY_DELETED"


def test_update_transaction_into_deleted_budget_returns_410(admin: TestClient) -> None:
    fun = add_budget(admin, "Fun")
    old = add_budget(admin, "Old")
    admin.delete(f"/api/v1/budgets/{old['id']}")
    created = _add(admin, fun["id"])
    response = admin.patch(
        f"/api/v1/transactions/{created['id']}", json={"budgetId": old["id"]}
    )
    assert response.status_code == 410


def test_update_transaction_out_of_period_returns_400(admin: TestClient) -> None:
    budget = add_budget(admin, "Fun")
    created = _add(admin, budget["id"])
    response = admin.patch(
        f"/api/v1/transactions/{created['id']}", json={"date": "2026-10-02"}
    )
    assert response.json()["code"] == "OUT_OF_PERIOD"


def test_update_transaction_with_zero_amount_returns_400(admin: TestClient) -> None:
    budget = add_budget(admin, "Fun")
    created = _add(admin, budget["id"])
    response = admin.patch(f"/api/v1/transactions/{created['id']}", json={"amount": 0})
    assert response.json()["field"] == "amount"


def test_update_unknown_or_deleted_transaction(admin: TestClient) -> None:
    budget = add_budget(admin, "Fun")
    created = _add(admin, budget["id"])
    admin.delete(f"/api/v1/transactions/{created['id']}")
    assert (
        admin.patch(f"/api/v1/transactions/{UNKNOWN}", json={"amount": -1}).status_code
        == 404
    )
    gone = admin.patch(f"/api/v1/transactions/{created['id']}", json={"amount": -1})
    assert gone.status_code == 410


def test_delete_transaction_soft_deletes_and_logs(
    admin: TestClient, db: Session
) -> None:
    budget = add_budget(admin, "Fun")
    created = _add(admin, budget["id"])
    assert admin.delete(f"/api/v1/transactions/{created['id']}").status_code == 204
    assert admin.get("/api/v1/transactions").json()["items"] == []
    assert _actions(db)[-1] == ("tx.delete", {"payee": "Corner Coffee"})


def test_delete_archived_transaction_returns_409(
    admin: TestClient, db: Session
) -> None:
    budget = add_budget(admin, "Groceries")
    old = insert_transaction(db, str(budget["id"]), -100, date(2026, 8, 30))
    assert admin.delete(f"/api/v1/transactions/{old.id}").status_code == 409


def test_bulk_delete_reports_deleted_and_not_found(
    admin: TestClient, db: Session
) -> None:
    budget = add_budget(admin, "Fun")
    first = _add(admin, budget["id"])
    second = _add(admin, budget["id"])
    response = admin.post(
        "/api/v1/transactions/bulk-delete",
        json={"ids": [first["id"], second["id"], first["id"], UNKNOWN]},
    )
    assert response.status_code == 200
    body = response.json()
    assert sorted(body["deleted"]) == sorted([str(first["id"]), str(second["id"])])
    assert body["notFound"] == [UNKNOWN]
    assert _actions(db)[-1] == ("tx.bulkDelete", {"count": 2})


def test_bulk_delete_twice_never_merges_counts(admin: TestClient, db: Session) -> None:
    budget = add_budget(admin, "Fun")
    first = _add(admin, budget["id"])
    second = _add(admin, budget["id"])
    admin.post("/api/v1/transactions/bulk-delete", json={"ids": [first["id"]]})
    admin.post("/api/v1/transactions/bulk-delete", json={"ids": [second["id"]]})
    assert [p for a, p in _actions(db) if a == "tx.bulkDelete"] == [
        {"count": 1},
        {"count": 1},
    ]


def test_bulk_delete_with_a_read_only_row_deletes_nothing(
    admin: TestClient, db: Session
) -> None:
    budget = add_budget(admin, "Groceries")
    current = _add(admin, budget["id"])
    old = insert_transaction(db, str(budget["id"]), -100, date(2026, 8, 30))
    response = admin.post(
        "/api/v1/transactions/bulk-delete", json={"ids": [current["id"], str(old.id)]}
    )
    assert response.status_code == 409
    assert len(admin.get("/api/v1/transactions").json()["items"]) == 1


def test_bulk_delete_with_a_deleted_category_row_returns_409(admin: TestClient) -> None:
    budget = add_budget(admin, "Fun")
    created = _add(admin, budget["id"])
    admin.delete(f"/api/v1/budgets/{budget['id']}")
    response = admin.post(
        "/api/v1/transactions/bulk-delete", json={"ids": [created["id"]]}
    )
    assert response.json()["code"] == "CATEGORY_DELETED"


def test_bulk_delete_of_nothing_found_changes_nothing(
    admin: TestClient, db: Session
) -> None:
    before = admin.get("/api/v1/transactions").headers["X-Ledger-Rev"]
    response = admin.post("/api/v1/transactions/bulk-delete", json={"ids": [UNKNOWN]})
    assert response.json() == {"deleted": [], "notFound": [UNKNOWN]}
    assert response.headers["X-Ledger-Rev"] == before


def test_bulk_delete_with_too_many_or_no_ids_returns_400(admin: TestClient) -> None:
    for ids in ([], [UNKNOWN] * 501):
        response = admin.post("/api/v1/transactions/bulk-delete", json={"ids": ids})
        assert response.status_code == 400


def test_transactions_respect_the_household_timezone(admin: TestClient) -> None:
    admin.patch("/api/v1/household", json={"timezone": "Pacific/Kiritimati"})
    budget = add_budget(admin, "Fun")
    body = _add(admin, budget["id"])
    # 10:00 UTC on Sep 28 is already Sep 29 at UTC+14.
    assert body["date"] == "2026-09-29"


def test_member_can_log_transactions(admin: TestClient, other: TestClient) -> None:
    budget = add_budget(admin, "Fun")
    add_member(admin, "jordan")
    sign_in(other, "jordan", "initial-pass")
    assert _add(other, budget["id"])["payee"] == "Corner Coffee"
