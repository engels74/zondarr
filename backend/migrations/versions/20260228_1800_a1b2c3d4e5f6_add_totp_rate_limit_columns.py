"""add totp rate limit and audit columns

Revision ID: a1b2c3d4e5f6
Revises: 6103f5e16ff6
Create Date: 2026-02-28 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "6103f5e16ff6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration changes."""
    with op.batch_alter_table("admin_accounts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("totp_enabled_at", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "totp_failed_attempts",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column("totp_last_failed_at", sa.DateTime(), nullable=True)
        )


def downgrade() -> None:
    """Revert migration changes."""
    with op.batch_alter_table("admin_accounts", schema=None) as batch_op:
        batch_op.drop_column("totp_last_failed_at")
        batch_op.drop_column("totp_failed_attempts")
        batch_op.drop_column("totp_enabled_at")
