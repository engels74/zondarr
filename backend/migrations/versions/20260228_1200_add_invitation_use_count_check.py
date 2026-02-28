"""add invitation use_count check constraint

Revision ID: 5a3e7f1b9c2d
Revises: 4dc4ed3ab54b
Create Date: 2026-02-28 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "5a3e7f1b9c2d"
down_revision: str | None = "4dc4ed3ab54b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration changes."""
    with op.batch_alter_table("invitations", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_invitations_use_count_le_max_uses",
            "max_uses IS NULL OR use_count <= max_uses",
        )


def downgrade() -> None:
    """Revert migration changes."""
    with op.batch_alter_table("invitations", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_invitations_use_count_le_max_uses", type_="check"
        )
