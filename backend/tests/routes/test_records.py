"""Tests for transaction (records) routes.

Covers CRUD, bulk delete, flow derivation, soft-deleted concept rejection.
"""

from datetime import date

from app import db
from app.models.concept import Concept
from app.models.transaction import Transaction


class TestListRecords:
    """GET /api/records tests."""

    def test_list_records_returns_transactions_for_month(self, auth_client, admin_user):
        concept = Concept(name="Salary", flow="IN", created_by=admin_user.id)
        db.session.add(concept)
        db.session.commit()

        t = Transaction(date=date(2026, 9, 15), concept_id=concept.id, amount=1000, user_id=admin_user.id)
        db.session.add(t)
        db.session.commit()

        resp = auth_client.get("/api/records?month=2026-09")
        assert resp.status_code == 200
        records = resp.get_json()["records"]
        assert len(records) == 1
        assert records[0]["flow"] == "IN"
        assert records[0]["concept_name"] == "Salary"

    def test_list_records_excludes_other_months(self, auth_client, admin_user):
        concept = Concept(name="Rent", flow="OUT", created_by=admin_user.id)
        db.session.add(concept)
        db.session.commit()

        t = Transaction(date=date(2026, 8, 1), concept_id=concept.id, amount=500, user_id=admin_user.id)
        db.session.add(t)
        db.session.commit()

        resp = auth_client.get("/api/records?month=2026-09")
        assert resp.status_code == 200
        assert len(resp.get_json()["records"]) == 0

    def test_list_records_without_month_returns_400(self, auth_client):
        resp = auth_client.get("/api/records")
        assert resp.status_code == 400

    def test_list_records_unauthenticated_returns_401(self, client):
        resp = client.get("/api/records?month=2026-09")
        assert resp.status_code == 401

    def test_list_records_with_filter(self, auth_client, admin_user):
        c1 = Concept(name="Salary", flow="IN", created_by=admin_user.id)
        c2 = Concept(name="Rent", flow="OUT", created_by=admin_user.id)
        db.session.add_all([c1, c2])
        db.session.commit()

        db.session.add(Transaction(date=date(2026, 9, 1), concept_id=c1.id, amount=1000, user_id=admin_user.id))
        db.session.add(Transaction(date=date(2026, 9, 2), concept_id=c2.id, amount=500, user_id=admin_user.id))
        db.session.commit()

        resp = auth_client.get("/api/records?month=2026-09&filter=sal")
        records = resp.get_json()["records"]
        assert len(records) == 1
        assert records[0]["concept_name"] == "Salary"


class TestCreateRecord:
    """POST /api/records tests."""

    def test_create_record_with_valid_data_returns_201(self, auth_client, admin_user):
        concept = Concept(name="Food", flow="OUT", created_by=admin_user.id)
        db.session.add(concept)
        db.session.commit()

        resp = auth_client.post("/api/records", json={
            "date": "2026-09-15", "concept_id": concept.id, "amount": 42.50,
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["amount"] == 42.5
        assert data["flow"] == "OUT"
        assert data["username"] == "admin"

    def test_create_record_with_deleted_concept_returns_400(self, auth_client, admin_user):
        concept = Concept(name="Old", flow="OUT", created_by=admin_user.id, is_deleted=True)
        db.session.add(concept)
        db.session.commit()

        resp = auth_client.post("/api/records", json={
            "date": "2026-09-15", "concept_id": concept.id, "amount": 10,
        })
        assert resp.status_code == 400

    def test_create_record_with_nonexistent_concept_returns_404(self, auth_client):
        resp = auth_client.post("/api/records", json={
            "date": "2026-09-15", "concept_id": 9999, "amount": 10,
        })
        assert resp.status_code == 404

    def test_create_record_with_invalid_date_returns_400(self, auth_client, admin_user):
        concept = Concept(name="Test", flow="OUT", created_by=admin_user.id)
        db.session.add(concept)
        db.session.commit()

        resp = auth_client.post("/api/records", json={
            "date": "not-a-date", "concept_id": concept.id, "amount": 10,
        })
        assert resp.status_code == 400


class TestUpdateRecord:
    """PUT /api/records/:id tests."""

    def test_update_record_amount(self, auth_client, admin_user):
        concept = Concept(name="Food", flow="OUT", created_by=admin_user.id)
        db.session.add(concept)
        db.session.commit()
        t = Transaction(date=date(2026, 9, 1), concept_id=concept.id, amount=10, user_id=admin_user.id)
        db.session.add(t)
        db.session.commit()

        resp = auth_client.put(f"/api/records/{t.id}", json={"amount": 25.50})
        assert resp.status_code == 200
        assert resp.get_json()["amount"] == 25.5

    def test_update_nonexistent_record_returns_404(self, auth_client):
        resp = auth_client.put("/api/records/9999", json={"amount": 10})
        assert resp.status_code == 404


class TestDeleteRecord:
    """DELETE /api/records/:id tests."""

    def test_delete_record_returns_200(self, auth_client, admin_user):
        concept = Concept(name="Temp", flow="OUT", created_by=admin_user.id)
        db.session.add(concept)
        db.session.commit()
        t = Transaction(date=date(2026, 9, 1), concept_id=concept.id, amount=10, user_id=admin_user.id)
        db.session.add(t)
        db.session.commit()

        resp = auth_client.delete(f"/api/records/{t.id}")
        assert resp.status_code == 200
        assert resp.get_json()["deleted"] is True
        assert db.session.get(Transaction, t.id) is None

    def test_delete_nonexistent_returns_404(self, auth_client):
        resp = auth_client.delete("/api/records/9999")
        assert resp.status_code == 404


class TestBulkDeleteRecords:
    """DELETE /api/records/bulk tests."""

    def test_bulk_delete_returns_count(self, auth_client, admin_user):
        concept = Concept(name="Bulk", flow="OUT", created_by=admin_user.id)
        db.session.add(concept)
        db.session.commit()
        transactions = []
        for i in range(3):
            t = Transaction(date=date(2026, 9, i + 1), concept_id=concept.id, amount=10, user_id=admin_user.id)
            db.session.add(t)
            transactions.append(t)
        db.session.commit()
        ids = [t.id for t in transactions]

        resp = auth_client.delete("/api/records/bulk", json={"ids": ids})
        assert resp.status_code == 200
        assert resp.get_json()["deleted_count"] == 3

    def test_bulk_delete_over_100_returns_400(self, auth_client):
        resp = auth_client.delete("/api/records/bulk", json={"ids": list(range(101))})
        assert resp.status_code == 400

    def test_bulk_delete_empty_ids_returns_400(self, auth_client):
        resp = auth_client.delete("/api/records/bulk", json={"ids": []})
        assert resp.status_code == 400
