"""011_drop_workspace_id_from_tables_and_categories

Revision ID: 011
Revises: 010
Create Date: 2026-05-16

Changes:
- tables: drop workspace_id (column, FK, index); persona_id SET NULL/nullable → CASCADE/NOT NULL
- categories: drop workspace_id (column, FK, index); persona_id SET NULL/nullable → CASCADE/NOT NULL
"""

import sqlalchemy as sa
from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # tables
    # ------------------------------------------------------------------ #

    # 1. Drop workspace_id FK + index + column
    op.drop_constraint("tables_workspace_id_fkey", "tables", type_="foreignkey")
    op.drop_index("ix_tables_workspace_id", table_name="tables")
    op.drop_column("tables", "workspace_id")

    # 2. Drop old persona_id FK (SET NULL)
    op.drop_constraint("tables_persona_id_fkey", "tables", type_="foreignkey")

    # 3. Make persona_id NOT NULL
    op.alter_column("tables", "persona_id", nullable=False)

    # 4. Re-add persona_id FK with CASCADE
    op.create_foreign_key(
        "tables_persona_id_fkey",
        "tables", "personas",
        ["persona_id"], ["id"],
        ondelete="CASCADE",
    )

    # ------------------------------------------------------------------ #
    # categories
    # ------------------------------------------------------------------ #

    # 1. Drop workspace_id FK + index + column
    op.drop_constraint("categories_workspace_id_fkey", "categories", type_="foreignkey")
    op.drop_index("ix_categories_workspace_id", table_name="categories")
    op.drop_column("categories", "workspace_id")

    # 2. Drop old persona_id FK (SET NULL)
    op.drop_constraint("categories_persona_id_fkey", "categories", type_="foreignkey")

    # 3. Make persona_id NOT NULL
    op.alter_column("categories", "persona_id", nullable=False)

    # 4. Re-add persona_id FK with CASCADE
    op.create_foreign_key(
        "categories_persona_id_fkey",
        "categories", "personas",
        ["persona_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # ------------------------------------------------------------------ #
    # categories
    # ------------------------------------------------------------------ #

    op.drop_constraint("categories_persona_id_fkey", "categories", type_="foreignkey")
    op.alter_column("categories", "persona_id", nullable=True)
    op.create_foreign_key(
        "categories_persona_id_fkey",
        "categories", "personas",
        ["persona_id"], ["id"],
        ondelete="SET NULL",
    )
    op.add_column("categories", sa.Column("workspace_id", sa.BigInteger(), nullable=False))
    op.create_foreign_key(
        "categories_workspace_id_fkey",
        "categories", "workspaces",
        ["workspace_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_categories_workspace_id", "categories", ["workspace_id"])

    # ------------------------------------------------------------------ #
    # tables
    # ------------------------------------------------------------------ #

    op.drop_constraint("tables_persona_id_fkey", "tables", type_="foreignkey")
    op.alter_column("tables", "persona_id", nullable=True)
    op.create_foreign_key(
        "tables_persona_id_fkey",
        "tables", "personas",
        ["persona_id"], ["id"],
        ondelete="SET NULL",
    )
    op.add_column("tables", sa.Column("workspace_id", sa.BigInteger(), nullable=False))
    op.create_foreign_key(
        "tables_workspace_id_fkey",
        "tables", "workspaces",
        ["workspace_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_tables_workspace_id", "tables", ["workspace_id"])
