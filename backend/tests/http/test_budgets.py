"""`/budgets` (API_SURFACE.md § 6, BACKEND.md § 4.2, § 6)."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.persistence.tables import activity
from app.domain.entities import Activity
from tests.helpers import add_budget, insert_transaction

SEPT = date(2026, 9, 10)
AUGUST = date(2026, 8, 10)


def _actions(db: Session) -> list[tuple[str, dict[str, object]]]:
    entries = db.scalars(select(Activity).order_by(activity.c.at))
    return [(e.action, e.params) for e in entries]


def test_create_budget_starts_at_zero(admin: TestClient) -> None:
    response = admin.post("/api/v1/budgets", json={"name": " Groceries "})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Groceries"
    assert body["amount"] == 0
    assert body["schedule"] is None
    assert body["goal"] is False
    assert body["actual"] == 0
    assert body["projected"] == 0
    assert body["over"] is False
    assert body["overBy"] == 0
    assert body["progressPct"] == 0


def test_create_budget_records_activity(admin: TestClient, db: Session) -> None:
    add_budget(admin, "Groceries")
    assert _actions(db) == [("budget.create", {"name": "Groceries"})]


def test_create_budget_with_duplicate_name_ignoring_case_returns_409(
    admin: TestClient,
) -> None:
    add_budget(admin, "Groceries")
    response = admin.post("/api/v1/budgets", json={"name": "groceries"})
    assert response.status_code == 409
    assert response.json()["field"] == "name"


def test_create_budget_reusing_a_deleted_name_returns_201(admin: TestClient) -> None:
    budget = add_budget(admin, "Rent")
    admin.delete(f"/api/v1/budgets/{budget['id']}")
    assert admin.post("/api/v1/budgets", json={"name": "Rent"}).status_code == 201


def test_create_budget_with_blank_name_returns_400(admin: TestClient) -> None:
    response = admin.post("/api/v1/budgets", json={"name": "   "})
    assert response.json()["field"] == "name"


def test_list_budgets_returns_period_and_figures(
    admin: TestClient, db: Session
) -> None:
    groceries = add_budget(admin, "Groceries", -80000)
    add_budget(admin, "Paycheck", 224000)
    insert_transaction(db, str(groceries["id"]), -60400, SEPT)
    insert_transaction(db, str(groceries["id"]), -9999, AUGUST)
    insert_transaction(db, str(groceries["id"]), -5000, SEPT, deleted=True)
    body = admin.get("/api/v1/budgets").json()
    assert body["period"] == {
        "month": "2026-09",
        "start": "2026-09-01",
        "end": "2026-09-30",
        "today": "2026-09-28",
        "daysInMonth": 30,
    }
    first, second = body["items"]
    assert first["name"] == "Groceries"
    assert first["actual"] == -60400
    assert first["projected"] == -80000
    assert first["remaining"] == -19600
    assert first["progressPct"] == 75.5
    assert second["name"] == "Paycheck"
    assert second["remaining"] == 224000


def test_list_budgets_excludes_deleted(admin: TestClient) -> None:
    budget = add_budget(admin, "Rent")
    admin.delete(f"/api/v1/budgets/{budget['id']}")
    assert admin.get("/api/v1/budgets").json()["items"] == []


def test_patch_budget_sets_amount_and_merges_activity(
    admin: TestClient, db: Session
) -> None:
    budget = add_budget(admin, "Groceries")
    admin.patch(f"/api/v1/budgets/{budget['id']}", json={"amount": -5000})
    response = admin.patch(f"/api/v1/budgets/{budget['id']}", json={"amount": -10000})
    assert response.json()["amount"] == -10000
    assert _actions(db) == [
        ("budget.create", {"name": "Groceries"}),
        ("budget.amount", {"name": "Groceries", "amount": -10000}),
    ]


def test_patch_budget_renames(admin: TestClient, db: Session) -> None:
    budget = add_budget(admin, "Grocery")
    response = admin.patch(
        f"/api/v1/budgets/{budget['id']}", json={"name": "Groceries"}
    )
    assert response.json()["name"] == "Groceries"
    assert _actions(db)[-1] == (
        "budget.rename",
        {"oldName": "Grocery", "name": "Groceries"},
    )


def test_patch_budget_rename_to_own_name_in_other_case_returns_200(
    admin: TestClient,
) -> None:
    budget = add_budget(admin, "rent")
    response = admin.patch(f"/api/v1/budgets/{budget['id']}", json={"name": "Rent"})
    assert response.json()["name"] == "Rent"


def test_patch_budget_rename_to_taken_name_returns_409(admin: TestClient) -> None:
    add_budget(admin, "Rent")
    budget = add_budget(admin, "Fun")
    response = admin.patch(f"/api/v1/budgets/{budget['id']}", json={"name": "RENT"})
    assert response.status_code == 409


def test_patch_budget_sets_and_clears_schedule(admin: TestClient, db: Session) -> None:
    budget = add_budget(admin, "Rent")
    schedule = {"repeat": "monthly", "anchor": "2026-10-01"}
    response = admin.patch(
        f"/api/v1/budgets/{budget['id']}", json={"schedule": schedule}
    )
    assert response.json()["schedule"] == schedule
    response = admin.patch(f"/api/v1/budgets/{budget['id']}", json={"schedule": None})
    assert response.json()["schedule"] is None
    assert _actions(db)[-1] == ("budget.schedule", {"name": "Rent"})


def test_patch_budget_with_bad_schedule_returns_400(admin: TestClient) -> None:
    budget = add_budget(admin, "Rent")
    for schedule in (
        {"repeat": "yearly", "anchor": "2026-10-01"},
        {"repeat": "monthly", "anchor": "2026-13-01"},
        {"repeat": "monthly", "anchor": 20261001},
        {"repeat": "monthly"},
    ):
        response = admin.patch(
            f"/api/v1/budgets/{budget['id']}", json={"schedule": schedule}
        )
        assert response.status_code == 400, schedule


def test_patch_budget_toggles_goal(admin: TestClient, db: Session) -> None:
    budget = add_budget(admin, "Lisbon trip")
    response = admin.patch(f"/api/v1/budgets/{budget['id']}", json={"goal": True})
    assert response.json()["goal"] is True
    assert _actions(db)[-1] == ("budget.goal", {"name": "Lisbon trip", "goal": True})


def test_patch_budget_with_unchanged_values_writes_no_activity(
    admin: TestClient, db: Session
) -> None:
    budget = add_budget(admin, "Rent")
    admin.patch(f"/api/v1/budgets/{budget['id']}", json={"amount": 0, "goal": False})
    assert _actions(db) == [("budget.create", {"name": "Rent"})]


def test_patch_budget_with_float_amount_returns_400(admin: TestClient) -> None:
    budget = add_budget(admin, "Rent")
    response = admin.patch(f"/api/v1/budgets/{budget['id']}", json={"amount": 1.5})
    assert response.json()["field"] == "amount"


def test_patch_budget_with_null_name_returns_400(admin: TestClient) -> None:
    budget = add_budget(admin, "Rent")
    response = admin.patch(f"/api/v1/budgets/{budget['id']}", json={"name": None})
    assert response.json()["field"] == "name"


def test_patch_unknown_budget_returns_404(admin: TestClient) -> None:
    response = admin.patch(
        "/api/v1/budgets/00000000-0000-4000-8000-000000000000", json={"amount": 1}
    )
    assert response.status_code == 404


def test_patch_deleted_budget_returns_410(admin: TestClient) -> None:
    budget = add_budget(admin, "Rent")
    admin.delete(f"/api/v1/budgets/{budget['id']}")
    response = admin.patch(f"/api/v1/budgets/{budget['id']}", json={"amount": 1})
    assert response.status_code == 410


def test_delete_budget_records_activity(admin: TestClient, db: Session) -> None:
    budget = add_budget(admin, "Rent")
    assert admin.delete(f"/api/v1/budgets/{budget['id']}").status_code == 204
    assert _actions(db)[-1] == ("budget.delete", {"name": "Rent"})


def test_delete_budget_twice_returns_410(admin: TestClient) -> None:
    budget = add_budget(admin, "Rent")
    admin.delete(f"/api/v1/budgets/{budget['id']}")
    assert admin.delete(f"/api/v1/budgets/{budget['id']}").status_code == 410


def test_delete_unknown_budget_returns_404(admin: TestClient) -> None:
    response = admin.delete("/api/v1/budgets/00000000-0000-4000-8000-000000000000")
    assert response.status_code == 404


def test_budgets_without_session_return_401(client: TestClient) -> None:
    assert client.get("/api/v1/budgets").status_code == 401
