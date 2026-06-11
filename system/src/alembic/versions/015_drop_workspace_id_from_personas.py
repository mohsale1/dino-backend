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

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop FK constraint
    op.drop_constraint("personas_workspace_id_fkey", "personas", type_="foreignkey")

    # 2. Drop index
    op.drop_index("ix_personas_workspace_id", table_name="personas")

    # 3. Drop column
    op.drop_column("personas", "workspace_id")


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
