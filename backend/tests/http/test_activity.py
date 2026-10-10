"""`/activity` and target resolution (API_SURFACE.md § 1.8, § 8)."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.entities import Activity
from tests.helpers import add_budget, add_member, insert_transaction


def _feed(client: TestClient, query: str = "") -> list[dict[str, object]]:
    items: list[dict[str, object]] = client.get(f"/api/v1/activity{query}").json()[
        "items"
    ]
    return items


def test_activity_lists_newest_first_with_actor_and_params(admin: TestClient) -> None:
    add_budget(admin, "Groceries")
    admin.patch("/api/v1/household", json={"currencySign": "€"})
    me = admin.get("/api/v1/auth/session").json()["member"]
    feed = _feed(admin)
    assert [e["action"] for e in feed] == ["settings.currency", "budget.create"]
    assert feed[0]["actorId"] == me["id"]
    assert feed[0]["params"] == {"sign": "€"}
    assert feed[0]["target"] == {"type": "settings", "section": "currency"}
    assert str(feed[0]["at"]).endswith("Z")


def test_activity_pages(admin: TestClient) -> None:
    for name in ("A", "B", "C"):
        add_budget(admin, name)
    body = admin.get("/api/v1/activity?page=2&size=2").json()
    assert [e["params"] for e in body["items"]] == [{"name": "A"}]
    assert body["total"] == 3


def test_activity_targets_resolve_current_state(admin: TestClient) -> None:
    budget = add_budget(admin, "Trip")
    admin.patch(f"/api/v1/budgets/{budget['id']}", json={"goal": True})
    created = admin.post(
        "/api/v1/transactions",
        json={"budgetId": budget["id"], "amount": -100},
    ).json()
    jordan = add_member(admin, "jordan")
    targets = [e["target"] for e in _feed(admin)]
    assert targets == [
        {"type": "member", "id": jordan["id"]},
        {
            "type": "transaction",
            "id": created["id"],
            "archived": False,
            "month": "2026-09",
        },
        {"type": "budget", "id": budget["id"], "goal": True},
        {"type": "budget", "id": budget["id"], "goal": True},
    ]


def test_activity_targets_of_deleted_records_are_none(admin: TestClient) -> None:
    budget = add_budget(admin, "Fun")
    created = admin.post(
        "/api/v1/transactions",
        json={"budgetId": budget["id"], "amount": -100},
    ).json()
    jordan = add_member(admin, "jordan")
    admin.delete(f"/api/v1/transactions/{created['id']}")
    admin.delete(f"/api/v1/members/{jordan['id']}")
    admin.delete(f"/api/v1/budgets/{budget['id']}")
    assert {str(e["target"]) for e in _feed(admin)} == {str({"type": "none"})}


def test_activity_target_of_archived_transaction(
    admin: TestClient, db: Session
) -> None:
    budget = add_budget(admin, "Groceries")
    old = insert_transaction(db, str(budget["id"]), -100, date(2026, 8, 30))
    entry = Activity(
        actor_id=old.member_id,
        action="tx.update",
        at=old.created_at,
        target_type="transaction",
        target_id=old.id,
        params={"category": "Groceries", "amount": -100},
    )
    db.add(entry)
    db.commit()
    target = _feed(admin)[-1]["target"]
    assert target == {
        "type": "transaction",
        "id": str(old.id),
        "archived": True,
        "month": "2026-08",
    }
