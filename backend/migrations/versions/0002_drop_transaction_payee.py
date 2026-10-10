"""Drop transactions.payee: a transaction is category, amount, member, date

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-10 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("transactions") as batch:
        batch.drop_column("payee")


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch:
        batch.add_column(
            sa.Column("payee", sa.String(length=120), nullable=False, server_default="")
        )
