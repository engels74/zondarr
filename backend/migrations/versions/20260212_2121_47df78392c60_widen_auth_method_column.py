"""widen_auth_method_column

Widen admin_accounts.auth_method from String(20) to String(50)
to support additional provider names.

Revision ID: 47df78392c60
Revises: 18295ce7ef76
Create Date: 2026-02-12 21:21:10.151128
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "47df78392c60"
down_revision: str | None = "18295ce7ef76"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Widen auth_method column to String(50)."""
    with op.batch_alter_table("admin_accounts", schema=None) as batch_op:
        batch_op.alter_column(
            "auth_method",
            type_=sa.String(length=50),
            existing_type=sa.String(length=20),
            existing_nullable=False,
            existing_server_default="local",
        )


def downgrade() -> None:
    """Revert auth_method column to String(20)."""
    with op.batch_alter_table("admin_accounts", schema=None) as batch_op:
        batch_op.alter_column(
            "auth_method",
            type_=sa.String(length=20),
            existing_type=sa.String(length=50),
            existing_nullable=False,
            existing_server_default="local",
        )
