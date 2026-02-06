"""Add invitation_id column and missing indexes to users table.

Revision ID: 003
Revises: 002
Create Date: 2026-02-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add invitation_id column and performance indexes to users table."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("invitation_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_users_invitation_id",
            "invitations",
            ["invitation_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_users_invitation_id", ["invitation_id"])
        batch_op.create_index("ix_users_media_server_id", ["media_server_id"])
        batch_op.create_index("ix_users_identity_id", ["identity_id"])
        batch_op.create_index("ix_users_enabled_expires", ["enabled", "expires_at"])


def downgrade() -> None:
    """Remove invitation_id column and indexes from users table."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index("ix_users_enabled_expires")
        batch_op.drop_index("ix_users_identity_id")
        batch_op.drop_index("ix_users_media_server_id")
        batch_op.drop_index("ix_users_invitation_id")
        batch_op.drop_constraint("fk_users_invitation_id", type_="foreignkey")
        batch_op.drop_column("invitation_id")
