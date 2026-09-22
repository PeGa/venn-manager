"""Additional tests to push coverage above 90%.

Covers error handlers, filter paths, validation edge cases, and user management.
"""

from datetime import date

from app import db
from app.models.budget import Budget
from app.models.concept import Concept
from app.models.transaction import Transaction


class TestErrorHandlers:
    """Global error handler coverage."""

    def test_404_returns_error_shape(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data
        assert "detail" in data

    def test_405_returns_error(self, auth_client, admin_user):
        resp = auth_client.patch("/api/records/1")
        assert resp.status_code == 405


class TestBudgetFilter:
    """Budget list filter coverage."""

    def test_list_budget_with_filter(self, auth_client, admin_user):
        c1 = Concept(name="Rent", flow="OUT", created_by=admin_user.id)
        c2 = Concept(name="Food", flow="OUT", created_by=admin_user.id)
        db.session.add_all([c1, c2])
        db.session.commit()
        db.session.add(Budget(date=date(2026, 9, 1), concept_id=c1.id, amount=500, user_id=admin_user.id))
        db.session.add(Budget(date=date(2026, 9, 1), concept_id=c2.id, amount=200, user_id=admin_user.id))
        db.session.commit()

        resp = auth_client.get("/api/budget?month=2026-09&filter=rent")
        entries = resp.get_json()["budget"]
        assert len(entries) == 1
        assert entries[0]["concept_name"] == "Rent"


class TestRecordFilter:
    """Record list filter coverage."""

    def test_list_records_filter_by_username(self, auth_client, admin_user):
        c = Concept(name="Test", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()
        db.session.add(Transaction(date=date(2026, 9, 1), concept_id=c.id, amount=10, user_id=admin_user.id))
        db.session.commit()

        resp = auth_client.get("/api/records?month=2026-09&filter=admin")
        records = resp.get_json()["records"]
        assert len(records) == 1


class TestUserManagement:
    """Additional user management coverage."""

    def test_update_user_password(self, auth_client, regular_user):
        resp = auth_client.put(f"/api/users/{regular_user.id}", json={
            "password": "newpass123",
        })
        assert resp.status_code == 200

    def test_update_user_toggle_admin(self, auth_client, regular_user):
        resp = auth_client.put(f"/api/users/{regular_user.id}", json={
            "is_admin": True,
        })
        assert resp.status_code == 200
        assert resp.get_json()["is_admin"] is True

    def test_update_user_username(self, auth_client, regular_user):
        resp = auth_client.put(f"/api/users/{regular_user.id}", json={
            "username": "renamed",
        })
        assert resp.status_code == 200
        assert resp.get_json()["username"] == "renamed"

    def test_create_user_missing_fields(self, auth_client):
        resp = auth_client.post("/api/users", json={"username": "x"})
        assert resp.status_code == 400

    def test_delete_second_admin(self, auth_client, admin_user, regular_user):
        """Can delete an admin if another admin exists."""
        auth_client.put(f"/api/users/{regular_user.id}", json={"is_admin": True})
        resp = auth_client.delete(f"/api/users/{regular_user.id}")
        assert resp.status_code == 200


class TestRecordValidation:
    """Record update validation coverage."""

    def test_update_record_concept(self, auth_client, admin_user):
        c1 = Concept(name="A", flow="OUT", created_by=admin_user.id)
        c2 = Concept(name="B", flow="OUT", created_by=admin_user.id)
        db.session.add_all([c1, c2])
        db.session.commit()
        t = Transaction(date=date(2026, 9, 1), concept_id=c1.id, amount=10, user_id=admin_user.id)
        db.session.add(t)
        db.session.commit()

        resp = auth_client.put(f"/api/records/{t.id}", json={"concept_id": c2.id})
        assert resp.status_code == 200
        assert resp.get_json()["concept_name"] == "B"

    def test_update_record_date(self, auth_client, admin_user):
        c = Concept(name="D", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()
        t = Transaction(date=date(2026, 9, 1), concept_id=c.id, amount=10, user_id=admin_user.id)
        db.session.add(t)
        db.session.commit()

        resp = auth_client.put(f"/api/records/{t.id}", json={"date": "2026-09-15"})
        assert resp.status_code == 200
        assert resp.get_json()["date"] == "2026-09-15"

    def test_bulk_delete_nonexistent_ids_silent(self, auth_client):
        resp = auth_client.delete("/api/records/bulk", json={"ids": [99998, 99999]})
        assert resp.status_code == 200
        assert resp.get_json()["deleted_count"] == 0


class TestBudgetValidation:
    """Budget update validation coverage."""

    def test_update_budget_concept(self, auth_client, admin_user):
        c1 = Concept(name="X", flow="OUT", created_by=admin_user.id)
        c2 = Concept(name="Y", flow="OUT", created_by=admin_user.id)
        db.session.add_all([c1, c2])
        db.session.commit()
        b = Budget(date=date(2026, 9, 1), concept_id=c1.id, amount=100, user_id=admin_user.id)
        db.session.add(b)
        db.session.commit()

        resp = auth_client.put(f"/api/budget/{b.id}", json={"concept_id": c2.id})
        assert resp.status_code == 200
        assert resp.get_json()["concept_name"] == "Y"

    def test_update_budget_set_null_amount(self, auth_client, admin_user):
        c = Concept(name="N", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()
        b = Budget(date=date(2026, 9, 1), concept_id=c.id, amount=100, user_id=admin_user.id)
        db.session.add(b)
        db.session.commit()

        resp = auth_client.put(f"/api/budget/{b.id}", json={"amount": None})
        assert resp.status_code == 200
        assert resp.get_json()["amount"] is None

    def test_bulk_delete_budget_nonexistent(self, auth_client):
        resp = auth_client.delete("/api/budget/bulk", json={"ids": [99998, 99999]})
        assert resp.status_code == 200
        assert resp.get_json()["deleted_count"] == 0


class TestConceptFilter:
    """Concept list filter coverage."""

    def test_filter_by_username(self, auth_client, admin_user):
        db.session.add(Concept(name="TestC", flow="IN", created_by=admin_user.id))
        db.session.commit()

        resp = auth_client.get("/api/concepts?filter=admin")
        concepts = resp.get_json()["concepts"]
        assert len(concepts) == 1


class TestHistoryFilter:
    """History filter coverage."""

    def test_history_with_filter(self, auth_client, admin_user):
        c = Concept(name="HistFilter", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()
        db.session.add(Transaction(date=date(2026, 8, 1), concept_id=c.id, amount=50, user_id=admin_user.id))
        db.session.commit()

        resp = auth_client.get("/api/history?month=2026-08&filter=hist")
        records = resp.get_json()["records"]
        assert len(records) == 1
