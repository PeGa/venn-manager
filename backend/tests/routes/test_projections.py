"""Tests for projection calculations.

Covers spend/earn projections with budget+actual logic, unbudgeted items,
and savings calculation. Uses fixed-precision Decimal arithmetic.
"""

from datetime import date
from decimal import Decimal

from app import db
from app.models.budget import Budget
from app.models.concept import Concept
from app.models.transaction import Transaction


class TestProjections:
    """GET /api/projections tests."""

    def test_spend_projection_uses_max_of_budget_and_actual(self, auth_client, admin_user):
        """When actual spending exceeds budget, actual replaces budget."""
        c = Concept(name="Food", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()

        db.session.add(Budget(date=date(2026, 9, 1), concept_id=c.id, amount=100, user_id=admin_user.id))
        db.session.add(Transaction(date=date(2026, 9, 5), concept_id=c.id, amount=150, user_id=admin_user.id))
        db.session.commit()

        resp = auth_client.get("/api/projections?month=2026-09")
        data = resp.get_json()
        assert data["spend_projection"] == 150.0  # max(100, 150)

    def test_spend_projection_uses_budget_when_higher(self, auth_client, admin_user):
        """When budget exceeds actual, budget is used."""
        c = Concept(name="Food", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()

        db.session.add(Budget(date=date(2026, 9, 1), concept_id=c.id, amount=200, user_id=admin_user.id))
        db.session.add(Transaction(date=date(2026, 9, 5), concept_id=c.id, amount=50, user_id=admin_user.id))
        db.session.commit()

        resp = auth_client.get("/api/projections?month=2026-09")
        data = resp.get_json()
        assert data["spend_projection"] == 200.0  # max(200, 50)

    def test_earn_projection_uses_min_of_budget_and_actual(self, auth_client, admin_user):
        """When actual earnings are below budget, actual replaces budget."""
        c = Concept(name="Salary", flow="IN", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()

        db.session.add(Budget(date=date(2026, 9, 1), concept_id=c.id, amount=2000, user_id=admin_user.id))
        db.session.add(Transaction(date=date(2026, 9, 5), concept_id=c.id, amount=1500, user_id=admin_user.id))
        db.session.commit()

        resp = auth_client.get("/api/projections?month=2026-09")
        data = resp.get_json()
        assert data["earn_projection"] == 1500.0  # min(2000, 1500)

    def test_unbudgeted_transactions_included(self, auth_client, admin_user):
        """Transactions without a budget entry are added directly."""
        budgeted = Concept(name="Rent", flow="OUT", created_by=admin_user.id)
        unbudgeted = Concept(name="Coffee", flow="OUT", created_by=admin_user.id)
        db.session.add_all([budgeted, unbudgeted])
        db.session.commit()

        db.session.add(Budget(date=date(2026, 9, 1), concept_id=budgeted.id, amount=500, user_id=admin_user.id))
        db.session.add(Transaction(date=date(2026, 9, 1), concept_id=budgeted.id, amount=500, user_id=admin_user.id))
        db.session.add(Transaction(date=date(2026, 9, 10), concept_id=unbudgeted.id, amount=15, user_id=admin_user.id))
        db.session.commit()

        resp = auth_client.get("/api/projections?month=2026-09")
        data = resp.get_json()
        assert data["spend_projection"] == 515.0  # max(500,500) + 15 unbudgeted

    def test_savings_projection_is_earn_minus_spend(self, auth_client, admin_user):
        c_in = Concept(name="Salary", flow="IN", created_by=admin_user.id)
        c_out = Concept(name="Rent", flow="OUT", created_by=admin_user.id)
        db.session.add_all([c_in, c_out])
        db.session.commit()

        db.session.add(Transaction(date=date(2026, 9, 1), concept_id=c_in.id, amount=3000, user_id=admin_user.id))
        db.session.add(Transaction(date=date(2026, 9, 1), concept_id=c_out.id, amount=1000, user_id=admin_user.id))
        db.session.commit()

        resp = auth_client.get("/api/projections?month=2026-09")
        data = resp.get_json()
        assert data["savings_projection"] == 2000.0

    def test_current_out_and_in(self, auth_client, admin_user):
        c_in = Concept(name="Pay", flow="IN", created_by=admin_user.id)
        c_out = Concept(name="Buy", flow="OUT", created_by=admin_user.id)
        db.session.add_all([c_in, c_out])
        db.session.commit()

        db.session.add(Transaction(date=date(2026, 9, 1), concept_id=c_in.id, amount=1000, user_id=admin_user.id))
        db.session.add(Transaction(date=date(2026, 9, 2), concept_id=c_out.id, amount=250, user_id=admin_user.id))
        db.session.add(Transaction(date=date(2026, 9, 3), concept_id=c_out.id, amount=75, user_id=admin_user.id))
        db.session.commit()

        resp = auth_client.get("/api/projections?month=2026-09")
        data = resp.get_json()
        assert data["current_in"] == 1000.0
        assert data["current_out"] == 325.0

    def test_projections_without_month_returns_400(self, auth_client):
        resp = auth_client.get("/api/projections")
        assert resp.status_code == 400
