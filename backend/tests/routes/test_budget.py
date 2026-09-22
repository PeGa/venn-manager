"""Tests for budget routes.

Covers CRUD, nullable amount, flow derivation, bulk delete.
"""

from datetime import date

from app import db
from app.models.budget import Budget
from app.models.concept import Concept


class TestListBudget:
    """GET /api/budget tests."""

    def test_list_budget_for_month(self, auth_client, admin_user):
        c = Concept(name="Rent", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()
        b = Budget(date=date(2026, 9, 1), concept_id=c.id, amount=500, user_id=admin_user.id)
        db.session.add(b)
        db.session.commit()

        resp = auth_client.get("/api/budget?month=2026-09")
        assert resp.status_code == 200
        entries = resp.get_json()["budget"]
        assert len(entries) == 1
        assert entries[0]["amount"] == 500.0
        assert entries[0]["flow"] == "OUT"

    def test_list_budget_without_month_returns_400(self, auth_client):
        resp = auth_client.get("/api/budget")
        assert resp.status_code == 400


class TestCreateBudget:
    """POST /api/budget tests."""

    def test_create_budget_with_amount(self, auth_client, admin_user):
        c = Concept(name="Food", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()

        resp = auth_client.post("/api/budget", json={
            "date": "2026-09-01", "concept_id": c.id, "amount": 300,
        })
        assert resp.status_code == 201
        assert resp.get_json()["amount"] == 300.0

    def test_create_budget_with_null_amount(self, auth_client, admin_user):
        c = Concept(name="Misc", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()

        resp = auth_client.post("/api/budget", json={
            "date": "2026-09-01", "concept_id": c.id, "amount": None,
        })
        assert resp.status_code == 201
        assert resp.get_json()["amount"] is None

    def test_create_budget_with_deleted_concept_returns_400(self, auth_client, admin_user):
        c = Concept(name="Old", flow="OUT", created_by=admin_user.id, is_deleted=True)
        db.session.add(c)
        db.session.commit()

        resp = auth_client.post("/api/budget", json={
            "date": "2026-09-01", "concept_id": c.id, "amount": 100,
        })
        assert resp.status_code == 400


class TestUpdateBudget:
    """PUT /api/budget/:id tests."""

    def test_update_budget_amount(self, auth_client, admin_user):
        c = Concept(name="Rent", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()
        b = Budget(date=date(2026, 9, 1), concept_id=c.id, amount=500, user_id=admin_user.id)
        db.session.add(b)
        db.session.commit()

        resp = auth_client.put(f"/api/budget/{b.id}", json={"amount": 600})
        assert resp.status_code == 200
        assert resp.get_json()["amount"] == 600.0

    def test_update_nonexistent_returns_404(self, auth_client):
        resp = auth_client.put("/api/budget/9999", json={"amount": 100})
        assert resp.status_code == 404


class TestDeleteBudget:
    """DELETE /api/budget/:id tests."""

    def test_hard_delete_budget(self, auth_client, admin_user):
        c = Concept(name="Temp", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()
        b = Budget(date=date(2026, 9, 1), concept_id=c.id, amount=100, user_id=admin_user.id)
        db.session.add(b)
        db.session.commit()

        resp = auth_client.delete(f"/api/budget/{b.id}")
        assert resp.status_code == 200
        assert db.session.get(Budget, b.id) is None


class TestBulkDeleteBudget:
    """DELETE /api/budget/bulk tests."""

    def test_bulk_delete_budget(self, auth_client, admin_user):
        c = Concept(name="Bulk", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()
        budgets = []
        for i in range(3):
            b = Budget(date=date(2026, 9, i + 1), concept_id=c.id, amount=100, user_id=admin_user.id)
            db.session.add(b)
            budgets.append(b)
        db.session.commit()
        ids = [b.id for b in budgets]

        resp = auth_client.delete("/api/budget/bulk", json={"ids": ids})
        assert resp.status_code == 200
        assert resp.get_json()["deleted_count"] == 3
