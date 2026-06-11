"""014_drop_owner_id_from_workspaces

Revision ID: 014
Revises: 013
Create Date: 2026-05-16

Changes:
- Drop owner_id column (FK→users.id, SET NULL) from workspaces table
"""

import sqlalchemy as sa
from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop FK constraint then column
    op.drop_constraint("workspaces_owner_id_fkey", "workspaces", type_="foreignkey")
    op.drop_column("workspaces", "owner_id")


def downgrade() -> None:
    # Re-add column (nullable — cannot restore data)
    op.add_column(
        "workspaces",
        sa.Column("owner_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "workspaces_owner_id_fkey",
        "workspaces", "users",
        ["owner_id"], ["id"],
        ondelete="SET NULL",
    )
