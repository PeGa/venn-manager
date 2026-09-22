"""Tests for concept routes.

Covers CRUD, soft delete, flow immutability, uniqueness constraints.
"""

from app import db
from app.models.concept import Concept


class TestListConcepts:
    """GET /api/concepts tests."""

    def test_list_concepts_excludes_deleted(self, auth_client, admin_user):
        db.session.add(Concept(name="Active", flow="IN", created_by=admin_user.id))
        db.session.add(Concept(name="Deleted", flow="OUT", created_by=admin_user.id, is_deleted=True))
        db.session.commit()

        resp = auth_client.get("/api/concepts")
        concepts = resp.get_json()["concepts"]
        assert len(concepts) == 1
        assert concepts[0]["name"] == "Active"

    def test_list_concepts_with_filter(self, auth_client, admin_user):
        db.session.add(Concept(name="Salary", flow="IN", created_by=admin_user.id))
        db.session.add(Concept(name="Rent", flow="OUT", created_by=admin_user.id))
        db.session.commit()

        resp = auth_client.get("/api/concepts?filter=sal")
        concepts = resp.get_json()["concepts"]
        assert len(concepts) == 1
        assert concepts[0]["name"] == "Salary"


class TestCreateConcept:
    """POST /api/concepts tests."""

    def test_create_concept_returns_201(self, auth_client):
        resp = auth_client.post("/api/concepts", json={"name": "Groceries", "flow": "OUT"})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Groceries"
        assert data["flow"] == "OUT"

    def test_create_concept_duplicate_returns_409(self, auth_client):
        auth_client.post("/api/concepts", json={"name": "Food", "flow": "OUT"})
        resp = auth_client.post("/api/concepts", json={"name": "Food", "flow": "OUT"})
        assert resp.status_code == 409

    def test_create_concept_same_name_different_flow_ok(self, auth_client):
        resp1 = auth_client.post("/api/concepts", json={"name": "Transfer", "flow": "IN"})
        resp2 = auth_client.post("/api/concepts", json={"name": "Transfer", "flow": "OUT"})
        assert resp1.status_code == 201
        assert resp2.status_code == 201

    def test_create_concept_invalid_flow_returns_400(self, auth_client):
        resp = auth_client.post("/api/concepts", json={"name": "Bad", "flow": "MAYBE"})
        assert resp.status_code == 400

    def test_create_concept_name_too_long_returns_400(self, auth_client):
        resp = auth_client.post("/api/concepts", json={"name": "x" * 65, "flow": "IN"})
        assert resp.status_code == 400


class TestUpdateConcept:
    """PUT /api/concepts/:id tests."""

    def test_update_concept_name(self, auth_client, admin_user):
        c = Concept(name="Old", flow="IN", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()

        resp = auth_client.put(f"/api/concepts/{c.id}", json={"name": "New"})
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "New"

    def test_update_concept_flow_rejected(self, auth_client, admin_user):
        c = Concept(name="Test", flow="IN", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()

        resp = auth_client.put(f"/api/concepts/{c.id}", json={"name": "Test", "flow": "OUT"})
        assert resp.status_code == 400

    def test_update_deleted_concept_returns_404(self, auth_client, admin_user):
        c = Concept(name="Gone", flow="IN", created_by=admin_user.id, is_deleted=True)
        db.session.add(c)
        db.session.commit()

        resp = auth_client.put(f"/api/concepts/{c.id}", json={"name": "Revived"})
        assert resp.status_code == 404


class TestDeleteConcept:
    """DELETE /api/concepts/:id tests."""

    def test_soft_delete_concept(self, auth_client, admin_user):
        c = Concept(name="Soft", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()

        resp = auth_client.delete(f"/api/concepts/{c.id}")
        assert resp.status_code == 200
        assert db.session.get(Concept, c.id).is_deleted is True

    def test_delete_already_deleted_returns_404(self, auth_client, admin_user):
        c = Concept(name="Gone", flow="OUT", created_by=admin_user.id, is_deleted=True)
        db.session.add(c)
        db.session.commit()

        resp = auth_client.delete(f"/api/concepts/{c.id}")
        assert resp.status_code == 404


class TestBulkDeleteConcepts:
    """DELETE /api/concepts/bulk tests."""

    def test_bulk_soft_delete(self, auth_client, admin_user):
        concepts = []
        for name in ["A", "B", "C"]:
            c = Concept(name=name, flow="OUT", created_by=admin_user.id)
            db.session.add(c)
            concepts.append(c)
        db.session.commit()
        ids = [c.id for c in concepts]

        resp = auth_client.delete("/api/concepts/bulk", json={"ids": ids})
        assert resp.status_code == 200
        assert resp.get_json()["deleted_count"] == 3
        for cid in ids:
            assert db.session.get(Concept, cid).is_deleted is True

    def test_bulk_delete_over_100_returns_400(self, auth_client):
        resp = auth_client.delete("/api/concepts/bulk", json={"ids": list(range(101))})
        assert resp.status_code == 400
