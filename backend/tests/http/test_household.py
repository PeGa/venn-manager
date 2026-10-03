"""`/household` (API_SURFACE.md § 4, BACKEND.md § 9)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.persistence.tables import activity
from app.domain.entities import Activity
from tests.helpers import add_member, sign_in


def _activity(db: Session) -> list[Activity]:
    return list(db.scalars(select(Activity).order_by(activity.c.at)))


def test_get_household_returns_settings_and_members(admin: TestClient) -> None:
    add_member(admin, "jordan")
    body = admin.get("/api/v1/household").json()
    assert body["name"] == "Hogar"
    assert body["currencySign"] == "$"
    assert body["timezone"] == "UTC"
    assert body["openingBalance"] == 0
    assert body["showMemberIncome"] is False
    assert [m["username"] for m in body["members"]] == ["admin", "jordan"]


def test_get_household_includes_removed_members(admin: TestClient) -> None:
    jordan = add_member(admin, "jordan")
    admin.delete(f"/api/v1/members/{jordan['id']}")
    members = admin.get("/api/v1/household").json()["members"]
    assert members[1]["status"] == "removed"


def test_patch_household_updates_every_field(admin: TestClient) -> None:
    response = admin.patch(
        "/api/v1/household",
        json={
            "name": "Okafor-Lind",
            "currencySign": "CHF",
            "timezone": "Europe/Berlin",
            "openingBalance": -125050,
            "showMemberIncome": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Okafor-Lind"
    assert body["currencySign"] == "CHF"
    assert body["timezone"] == "Europe/Berlin"
    assert body["openingBalance"] == -125050
    assert body["showMemberIncome"] is True


def test_patch_household_writes_one_activity_per_changed_field(
    admin: TestClient, db: Session
) -> None:
    admin.patch("/api/v1/household", json={"name": "Hogar", "currencySign": "€"})
    entries = _activity(db)
    assert [(e.action, e.params) for e in entries] == [
        ("settings.currency", {"sign": "€"})
    ]
    assert entries[0].target_type == "settings"
    assert entries[0].target_section == "currency"


def test_patch_household_twice_merges_currency_entries(
    admin: TestClient, db: Session
) -> None:
    admin.patch("/api/v1/household", json={"currencySign": "€"})
    admin.patch("/api/v1/household", json={"currencySign": "£"})
    entries = _activity(db)
    assert len(entries) == 1
    assert entries[0].params == {"sign": "£"}


def test_patch_household_household_fields_target_household_section(
    admin: TestClient, db: Session
) -> None:
    admin.patch(
        "/api/v1/household",
        json={
            "name": "Casa",
            "timezone": "Europe/Madrid",
            "openingBalance": 500,
            "showMemberIncome": True,
        },
    )
    entries = _activity(db)
    assert [(e.action, e.params) for e in entries] == [
        ("settings.name", {"name": "Casa"}),
        ("settings.timezone", {"timezone": "Europe/Madrid"}),
        ("settings.openingBalance", {"amount": 500}),
        ("settings.memberIncome", {"enabled": True}),
    ]
    assert {e.target_section for e in entries} == {"household"}


def test_patch_household_allows_empty_currency_sign(admin: TestClient) -> None:
    response = admin.patch("/api/v1/household", json={"currencySign": "  "})
    assert response.json()["currencySign"] == ""


def test_patch_household_with_long_currency_sign_returns_400(
    admin: TestClient,
) -> None:
    response = admin.patch("/api/v1/household", json={"currencySign": "123456789"})
    assert response.json()["field"] == "currencySign"


def test_patch_household_with_unknown_timezone_returns_400(admin: TestClient) -> None:
    response = admin.patch("/api/v1/household", json={"timezone": "Mars/Base"})
    assert response.status_code == 400
    assert response.json()["field"] == "timezone"


def test_patch_household_with_float_balance_returns_400(admin: TestClient) -> None:
    response = admin.patch("/api/v1/household", json={"openingBalance": 10.5})
    assert response.json()["field"] == "openingBalance"


def test_patch_household_with_empty_body_returns_400(admin: TestClient) -> None:
    assert admin.patch("/api/v1/household", json={}).status_code == 400


def test_patch_household_bumps_revision_once(admin: TestClient) -> None:
    before = int(admin.get("/api/v1/household").headers["X-Ledger-Rev"])
    response = admin.patch("/api/v1/household", json={"name": "A", "currencySign": "€"})
    assert int(response.headers["X-Ledger-Rev"]) == before + 1


def test_patch_household_as_member_is_allowed(
    admin: TestClient, other: TestClient
) -> None:
    add_member(admin, "jordan")
    sign_in(other, "jordan", "initial-pass")
    assert other.patch("/api/v1/household", json={"name": "X"}).status_code == 200
