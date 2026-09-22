"""Tests for month switch routes.

Covers status detection, switch execution, day clamping.
"""

from datetime import date

from app import db
from app.models.budget import Budget
from app.models.concept import Concept


class TestMonthStatus:
    """GET /api/month/status tests."""

    def test_month_status_returns_shape(self, auth_client):
        resp = auth_client.get("/api/month/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "current_month" in data
        assert "active_month" in data
        assert "switch_available" in data


class TestMonthSwitch:
    """POST /api/month/switch tests."""

    def test_switch_updates_budget_dates(self, auth_client, admin_user, app, monkeypatch):
        """Budget dates are moved to the new month with day clamping."""
        from datetime import datetime

        # Fake the server date to October 2026
        class FakeDateTime:
            @classmethod
            def now(cls):
                return datetime(2026, 10, 15)

        monkeypatch.setattr("app.routes.month.datetime", FakeDateTime)

        c = Concept(name="Rent", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()

        # Budget entry with day 31 (should clamp to 30 in November, or stay in Oct)
        b = Budget(date=date(2026, 9, 15), concept_id=c.id, amount=500, user_id=admin_user.id)
        db.session.add(b)
        db.session.commit()

        resp = auth_client.post("/api/month/switch")
        assert resp.status_code == 200
        assert resp.get_json()["switched"] is True

        updated = db.session.get(Budget, b.id)
        assert updated.date.month == 10
        assert updated.date.day == 15

    def test_switch_clamps_day(self, auth_client, admin_user, monkeypatch):
        """Day 31 in a month with 30 days clamps to 30."""
        from datetime import datetime

        class FakeDateTime:
            @classmethod
            def now(cls):
                return datetime(2026, 6, 10)  # June has 30 days

        monkeypatch.setattr("app.routes.month.datetime", FakeDateTime)

        c = Concept(name="Test", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()

        b = Budget(date=date(2026, 5, 31), concept_id=c.id, amount=100, user_id=admin_user.id)
        db.session.add(b)
        db.session.commit()

        resp = auth_client.post("/api/month/switch")
        assert resp.status_code == 200
        updated = db.session.get(Budget, b.id)
        assert updated.date.day == 30  # June has 30 days

    def test_switch_when_not_available_returns_400(self, auth_client):
        resp = auth_client.post("/api/month/switch")
        assert resp.status_code == 400
