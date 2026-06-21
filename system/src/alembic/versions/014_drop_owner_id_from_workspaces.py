"""014_drop_owner_id_from_workspaces

Revision ID: 014
Revises: 013
Create Date: 2026-05-16

Changes:
- Drop owner_id column (FK→users.id, SET NULL) from workspaces table
"""

import sqlalchemy as sa
from alembic import op

revision = "b9c0d1e2f3a5"
down_revision = "a8b9c0d1e2f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE workspaces DROP CONSTRAINT IF EXISTS workspaces_owner_id_fkey"))
    conn.execute(sa.text("ALTER TABLE workspaces DROP COLUMN IF EXISTS owner_id"))

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