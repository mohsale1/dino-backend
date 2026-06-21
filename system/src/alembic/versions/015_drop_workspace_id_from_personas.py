"""015_drop_workspace_id_from_personas

Revision ID: 015
Revises: 014
Create Date: 2026-05-16

Changes:
- Drop workspace_id column (FK→workspaces.id CASCADE) from personas table
- Drop index ix_personas_workspace_id
- Workspace association is fully managed via workspace_personas join table
"""

import sqlalchemy as sa
from alembic import op

revision = "c0d1e2f3a4b6"
down_revision = "b9c0d1e2f3a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE personas DROP CONSTRAINT IF EXISTS personas_workspace_id_fkey"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_personas_workspace_id"))
    conn.execute(sa.text("ALTER TABLE personas DROP COLUMN IF EXISTS workspace_id"))

def downgrade() -> None:
    # Re-add column (nullable — cannot restore data)
    op.add_column(
        "personas",
        sa.Column("workspace_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "personas_workspace_id_fkey",
        "personas", "workspaces",
        ["workspace_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_personas_workspace_id", "personas", ["workspace_id"])
