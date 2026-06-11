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

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop the workspace_id FK constraint
    op.drop_constraint("areas_workspace_id_fkey", "areas", type_="foreignkey")

    # 2. Drop the workspace_id index
    op.drop_index("ix_areas_workspace_id", table_name="areas")

    # 3. Drop the workspace_id column
    op.drop_column("areas", "workspace_id")

    # 4. Drop old persona_id FK (SET NULL, nullable)
    op.drop_constraint("areas_persona_id_fkey", "areas", type_="foreignkey")

    # 5. Make persona_id NOT NULL
    op.alter_column("areas", "persona_id", nullable=False)

    # 6. Re-add persona_id FK with CASCADE
    op.create_foreign_key(
        "areas_persona_id_fkey",
        "areas",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="CASCADE",
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
