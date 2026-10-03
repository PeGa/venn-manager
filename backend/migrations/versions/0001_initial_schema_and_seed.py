"""Initial schema and first-run seed (BACKEND.md § 2, § 11)

Revision ID: 0001
Revises:
Create Date: 2026-10-03 03:19:05.879660
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session

from app.adapters.persistence.repositories import SqlUnitOfWork
from app.adapters.persistence.tables import UTCDateTime
from app.adapters.security import Argon2Hasher
from app.application.seed import seed
from app.config import settings_from_env

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "household",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("currency_sign", sa.String(length=8), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("opening_balance", sa.BigInteger(), nullable=False),
        sa.Column("show_member_income", sa.Boolean(), nullable=False),
        sa.Column("rev", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("real_name", sa.String(length=128), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("language", sa.String(length=2), nullable=True),
        sa.Column("theme", sa.String(length=6), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("is_removed", sa.Boolean(), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "activity",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("target_section", sa.String(length=16), nullable=True),
        sa.Column("at", UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("activity", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_activity_at"), ["at"], unique=False)

    op.create_table(
        "budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("schedule_repeat", sa.String(length=8), nullable=True),
        sa.Column("schedule_anchor", sa.Date(), nullable=True),
        sa.Column("is_goal", sa.Boolean(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("budgets", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_budgets_name"), ["name"], unique=False)

    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_sessions_token_hash"), ["token_hash"], unique=True
        )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payee", sa.String(length=120), nullable=False),
        sa.Column("budget_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["budget_id"],
            ["budgets.id"],
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_transactions_budget_id"), ["budget_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_transactions_date"), ["date"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_transactions_member_id"), ["member_id"], unique=False
        )

    _seed()


def _seed() -> None:
    """Insert the household and first admin inside this migration's transaction."""
    settings = settings_from_env()
    with Session(bind=op.get_bind()) as db:
        seed(
            SqlUnitOfWork(db),
            Argon2Hasher(),
            admin_username=settings.default_admin_username,
            admin_password=settings.default_admin_password,
            timezone=settings.default_timezone,
            now=datetime.now(UTC),
        )
        db.flush()


def downgrade() -> None:
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_transactions_member_id"))
        batch_op.drop_index(batch_op.f("ix_transactions_date"))
        batch_op.drop_index(batch_op.f("ix_transactions_budget_id"))

    op.drop_table("transactions")
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sessions_token_hash"))

    op.drop_table("sessions")
    with op.batch_alter_table("budgets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_budgets_name"))

    op.drop_table("budgets")
    with op.batch_alter_table("activity", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_activity_at"))

    op.drop_table("activity")
    op.drop_table("users")
    op.drop_table("household")
