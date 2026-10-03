"""Model-level tests: constraints, defaults, indexes and decimal handling."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest
from flask import Flask
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import Base, db
from app.models import Budget, Concept, Setting, Transaction, User, user as user_model


def _indexed_columns(table_name: str) -> list[set[str]]:
    """Return the indexed column sets registered on the shared metadata.

    Read from `Base.metadata` rather than the mapped class, so the assertion
    also proves the table is registered where Alembic and `create_all()`
    look for it.
    """
    table = Base.metadata.tables[table_name]
    return [{column.name for column in index.columns} for index in table.indexes]


class TestUser:
    def test_create_hashes_password_with_werkzeug_default(self, app: Flask) -> None:
        # AGENTS.md § Authentication & Session Security: werkzeug's default
        # method, which is scrypt since Werkzeug 3.x.
        user = User.create(username="alice", password="secret-pass")

        assert user.password_hash.startswith("scrypt:")
        assert user.password_hash != "secret-pass"

    def test_defaults_are_not_admin_and_not_deleted(self, app: Flask) -> None:
        db.session.add(User.create(username="alice", password="secret-pass"))
        db.session.commit()

        user = db.session.scalar(select(User))

        assert user is not None
        assert user.is_admin is False
        assert user.is_deleted is False
        assert user.created_at is not None

    @pytest.mark.production_hashing
    def test_production_uses_werkzeug_default_scrypt_parameters(self) -> None:
        """Pin what production really hashes with.

        Every other test runs at a lowered work factor, so without this a typo in
        HASH_METHOD — or a future default change in werkzeug — would pass silently.
        """
        assert user_model.HASH_METHOD == "scrypt"

        user = User.create(username="probe", password="a-probe-password")

        assert user.password_hash.startswith("scrypt:32768:8:1$")
        assert user.verify_password("a-probe-password") is True

    def test_password_check_accepts_correct_and_rejects_wrong(self, app: Flask) -> None:
        user = User.create(username="alice", password="secret-pass")

        assert user.verify_password("secret-pass") is True
        assert user.verify_password("wrong") is False

    def test_duplicate_username_violates_unique_constraint(
        self, make_user: Callable[..., User]
    ) -> None:
        make_user("alice")
        db.session.add(User.create(username="alice", password="another-pass"))

        with pytest.raises(IntegrityError):
            db.session.commit()


class TestConcept:
    def test_flow_and_name_are_required(self, app: Flask) -> None:
        db.session.add(Concept(name=None, flow="out"))

        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_flow_check_constraint_rejects_unknown_value(self, app: Flask) -> None:
        db.session.add(Concept(name="Bogus", flow="sideways"))

        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_name_is_indexed(self, app: Flask) -> None:
        assert {"name"} in _indexed_columns("concepts")


class TestTransaction:
    def test_amount_round_trips_as_two_place_decimal(
        self,
        make_user: Callable[..., User],
        make_concept: Callable[..., Concept],
        make_transaction: Callable[..., Transaction],
    ) -> None:
        user = make_user("alice")
        concept = make_concept("Groceries", flow="out", created_by=user)

        make_transaction(
            concept=concept, user=user, amount="45.50", on=date(2025, 7, 1)
        )
        db.session.expunge_all()
        stored = db.session.get(Transaction, 1)

        assert stored is not None
        assert stored.amount == Decimal("45.50")
        assert isinstance(stored.amount, Decimal)

    def test_amount_is_required(
        self, make_user: Callable[..., User], make_concept: Callable[..., Concept]
    ) -> None:
        user = make_user("alice")
        concept = make_concept("Groceries", flow="out", created_by=user)
        db.session.add(
            Transaction(date=date(2025, 7, 1), concept_id=concept.id, user_id=user.id)
        )

        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_date_and_concept_are_indexed(self, app: Flask) -> None:
        indexed = _indexed_columns("transactions")

        assert {"date"} in indexed
        assert {"concept_id"} in indexed


class TestBudget:
    def test_amount_may_be_null(
        self,
        make_user: Callable[..., User],
        make_concept: Callable[..., Concept],
        make_budget: Callable[..., Budget],
    ) -> None:
        user = make_user("alice")
        concept = make_concept("Rent", flow="out", created_by=user)

        budget = make_budget(
            concept=concept, user=user, amount=None, on=date(2025, 7, 5)
        )

        assert budget.amount is None

    def test_date_and_concept_are_indexed(self, app: Flask) -> None:
        indexed = _indexed_columns("budgets")

        assert {"date"} in indexed
        assert {"concept_id"} in indexed


class TestSetting:
    def test_global_rows_carry_a_null_user(self, app: Flask) -> None:
        db.session.add(Setting(key="theme", value="dark", user_id=None))

        db.session.commit()

        stored = db.session.scalar(select(Setting))
        assert stored is not None
        assert stored.user_id is None
        assert stored.requires_admin is False

    def test_same_key_is_allowed_for_different_users(
        self, make_user: Callable[..., User]
    ) -> None:
        alice = make_user("alice")
        bob = make_user("bob")
        db.session.add_all(
            [
                Setting(key="theme", value="dark", user_id=alice.id),
                Setting(key="theme", value="light", user_id=bob.id),
            ]
        )

        db.session.commit()

        assert len(db.session.scalars(select(Setting)).all()) == 2
