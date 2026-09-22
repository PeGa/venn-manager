"""Tests for history routes.

Covers read-only access to past months, month listing, current month rejection.
"""

from datetime import date, datetime

from app import db
from app.models.concept import Concept
from app.models.transaction import Transaction


class TestGetHistory:
    """GET /api/history tests."""

    def test_get_history_for_past_month(self, auth_client, admin_user):
        c = Concept(name="Old", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()
        t = Transaction(date=date(2026, 8, 15), concept_id=c.id, amount=100, user_id=admin_user.id)
        db.session.add(t)
        db.session.commit()

        resp = auth_client.get("/api/history?month=2026-08")
        assert resp.status_code == 200
        records = resp.get_json()["records"]
        assert len(records) == 1

    def test_get_history_current_month_returns_400(self, auth_client):
        current = datetime.now().strftime("%Y-%m")
        resp = auth_client.get(f"/api/history?month={current}")
        assert resp.status_code == 400

    def test_get_history_future_month_returns_400(self, auth_client):
        resp = auth_client.get("/api/history?month=2099-01")
        assert resp.status_code == 400


class TestGetHistoryMonths:
    """GET /api/history/months tests."""

    def test_get_history_months_excludes_current(self, auth_client, admin_user):
        c = Concept(name="Past", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()
        t = Transaction(date=date(2026, 7, 1), concept_id=c.id, amount=50, user_id=admin_user.id)
        db.session.add(t)
        db.session.commit()

        resp = auth_client.get("/api/history/months")
        assert resp.status_code == 200
        months = resp.get_json()["months"]
        current = datetime.now().strftime("%Y-%m")
        assert current not in months

    def test_get_history_months_descending_order(self, auth_client, admin_user):
        c = Concept(name="Multi", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()
        db.session.add(Transaction(date=date(2026, 6, 1), concept_id=c.id, amount=10, user_id=admin_user.id))
        db.session.add(Transaction(date=date(2026, 7, 1), concept_id=c.id, amount=20, user_id=admin_user.id))
        db.session.add(Transaction(date=date(2026, 8, 1), concept_id=c.id, amount=30, user_id=admin_user.id))
        db.session.commit()

        resp = auth_client.get("/api/history/months")
        months = resp.get_json()["months"]
        assert months == sorted(months, reverse=True)
