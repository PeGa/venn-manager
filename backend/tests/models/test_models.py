"""Tests for model validations and constraints."""

from datetime import date
from decimal import Decimal

from app import db
from app.models.budget import Budget
from app.models.concept import Concept
from app.models.settings import Settings
from app.models.transaction import Transaction
from app.models.user import User


class TestUserModel:
    """User model tests."""

    def test_user_to_dict_excludes_password_hash(self, admin_user):
        d = admin_user.to_dict()
        assert "password_hash" not in d

    def test_user_to_dict_include_sensitive(self, admin_user):
        d = admin_user.to_dict(include_sensitive=True)
        assert "must_change_password" in d


class TestConceptModel:
    """Concept model tests."""

    def test_concept_to_dict(self, admin_user):
        c = Concept(name="Test", flow="IN", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()
        d = c.to_dict()
        assert d["name"] == "Test"
        assert d["flow"] == "IN"
        assert d["username"] == "admin"


class TestTransactionModel:
    """Transaction model tests."""

    def test_transaction_derives_flow_from_concept(self, admin_user):
        c = Concept(name="Salary", flow="IN", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()
        t = Transaction(date=date(2026, 9, 1), concept_id=c.id, amount=1000, user_id=admin_user.id)
        db.session.add(t)
        db.session.commit()
        d = t.to_dict()
        assert d["flow"] == "IN"

    def test_transaction_amount_precision(self, admin_user):
        c = Concept(name="Precise", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()
        t = Transaction(date=date(2026, 9, 1), concept_id=c.id, amount=Decimal("0.10"), user_id=admin_user.id)
        db.session.add(t)
        db.session.commit()
        loaded = db.session.get(Transaction, t.id)
        assert loaded.amount == Decimal("0.10")


class TestBudgetModel:
    """Budget model tests."""

    def test_budget_nullable_amount(self, admin_user):
        c = Concept(name="Maybe", flow="OUT", created_by=admin_user.id)
        db.session.add(c)
        db.session.commit()
        b = Budget(date=date(2026, 9, 1), concept_id=c.id, amount=None, user_id=admin_user.id)
        db.session.add(b)
        db.session.commit()
        loaded = db.session.get(Budget, b.id)
        assert loaded.amount is None


class TestSettingsModel:
    """Settings model tests."""

    def test_settings_default_currency(self):
        s = Settings.query.first()
        assert s is not None
        assert s.currency == "$"
