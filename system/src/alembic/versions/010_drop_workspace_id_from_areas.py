"""010_drop_workspace_id_from_areas

Revision ID: 010
Revises: 009
Create Date: 2026-05-16

Changes:
- Drop workspace_id column (+ FK + index) from areas table
- Change persona_id FK from SET NULL / nullable to CASCADE / NOT NULL
"""

import sqlalchemy as sa
from alembic import op

revision = "d5e6f7a8b9c1"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE areas DROP CONSTRAINT IF EXISTS areas_workspace_id_fkey"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_areas_workspace_id"))
    conn.execute(sa.text("ALTER TABLE areas DROP COLUMN IF EXISTS workspace_id"))
    conn.execute(sa.text("ALTER TABLE areas DROP CONSTRAINT IF EXISTS areas_persona_id_fkey"))
    op.alter_column("areas", "persona_id", nullable=False)
    conn.execute(sa.text("ALTER TABLE areas DROP CONSTRAINT IF EXISTS areas_persona_id_fkey"))
    op.create_foreign_key(
        "areas_persona_id_fkey", "areas", "personas",
        ["persona_id"], ["id"], ondelete="CASCADE",
    )

def downgrade() -> None:
    # 1. Drop CASCADE FK on persona_id
    op.drop_constraint("areas_persona_id_fkey", "areas", type_="foreignkey")

    # 2. Make persona_id nullable again
    op.alter_column("areas", "persona_id", nullable=True)

    # 3. Re-add SET NULL FK on persona_id
    op.create_foreign_key(
        "areas_persona_id_fkey",
        "areas",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 4. Re-add workspace_id column
    op.add_column(
        "areas",
        sa.Column(
            "workspace_id",
            sa.BigInteger(),
            nullable=False,
        ),
    )

    # 5. Re-add workspace_id FK
    op.create_foreign_key(
        "areas_workspace_id_fkey",
        "areas",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 6. Re-add workspace_id index
    op.create_index("ix_areas_workspace_id", "areas", ["workspace_id"])