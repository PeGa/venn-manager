"""Initial migration, seeding and model/migration drift (BACKEND.md § 2, § 11)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.persistence.repositories import SqlUnitOfWork, make_engine
from app.adapters.persistence.tables import metadata
from app.adapters.security import Argon2Hasher
from app.application.seed import seed
from app.domain.entities import Household, Member

BACKEND_ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 9, 1, tzinfo=UTC)


def _upgrade(url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DEFAULT_ADMIN_USERNAME", "root")
    monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "first-pass")
    monkeypatch.setenv("DEFAULT_TIMEZONE", "Europe/Madrid")
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    command.upgrade(config, "head")


def test_upgrade_head_seeds_household_and_admin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = f"sqlite:///{tmp_path / 'venn.db'}"
    _upgrade(url, monkeypatch)
    engine = make_engine(url)
    with Session(engine) as db:
        household = db.scalars(select(Household)).one()
        admin = db.scalars(select(Member)).one()
    engine.dispose()
    assert household.name == "Hogar"
    assert household.currency_sign == "$"
    assert household.timezone == "Europe/Madrid"
    assert household.rev == 1
    assert admin.username == "root"
    assert admin.real_name == "Administrador"
    assert admin.is_admin is True
    assert admin.must_change_password is True
    assert admin.language is None
    assert admin.theme == "system"
    assert Argon2Hasher().verify(admin.password_hash, "first-pass")


def test_upgrade_head_matches_models(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = f"sqlite:///{tmp_path / 'venn.db'}"
    _upgrade(url, monkeypatch)
    engine = make_engine(url)
    with engine.connect() as connection:
        drift = compare_metadata(MigrationContext.configure(connection), metadata)
    engine.dispose()
    assert drift == []


def test_seed_twice_creates_one_household(db: Session, hasher: Argon2Hasher) -> None:
    for _ in range(2):
        seed(
            SqlUnitOfWork(db),
            hasher,
            admin_username="admin",
            admin_password="admin",
            timezone="UTC",
            now=NOW,
        )
        db.commit()
    assert db.scalar(select(func.count()).select_from(Household)) == 1
    assert db.scalar(select(func.count()).select_from(Member)) == 1
