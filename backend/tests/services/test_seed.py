"""Seeding tests (CONTRACTS/BACKEND.md § 4)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.extensions import DbSession
from app.models import Concept, Setting, User
from app.services.seed import seed_initial_data

TODAY = date(2025, 7, 15)


def _seed(session: DbSession, username: str = "admin", password: str = "admin") -> bool:
    return seed_initial_data(
        session, admin_username=username, admin_password=password, today=TODAY
    )


class TestSeedInitialData:
    def test_first_run_returns_true(self, session: DbSession) -> None:
        assert _seed(session) is True

    def test_creates_admin_from_supplied_credentials(self, session: DbSession) -> None:
        _seed(session, username="root", password="root-pass")

        admin = session.scalar(select(User).where(User.username == "root"))

        assert admin is not None
        assert admin.real_name == "Administrator"
        assert admin.is_admin is True
        assert admin.is_deleted is False
        assert admin.verify_password("root-pass") is True

    def test_password_is_hashed_not_stored_in_clear(self, session: DbSession) -> None:
        _seed(session)

        admin = session.scalar(select(User).where(User.username == "admin"))

        assert admin is not None
        assert admin.password_hash != "admin"
        assert admin.password_hash.startswith("scrypt:")

    def test_second_run_is_a_no_op(self, session: DbSession) -> None:
        _seed(session)

        assert _seed(session) is False
        assert len(session.scalars(select(User)).all()) == 1

    def test_writes_global_settings_defaults(self, session: DbSession) -> None:
        _seed(session)

        values = {s.key: s.value for s in session.scalars(select(Setting)).all()}

        assert values == {
            "currency": "$",
            "language": "en",
            "theme": "system",
            "last_acknowledged_month": "2025-07",
        }

    def test_settings_are_global_rows(self, session: DbSession) -> None:
        _seed(session)

        owners = {s.user_id for s in session.scalars(select(Setting)).all()}

        assert owners == {None}

    def test_creates_no_concepts(self, session: DbSession) -> None:
        _seed(session)

        assert session.scalar(select(Concept)) is None
