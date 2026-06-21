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

revision = "e6f7a8b9c0d2"
down_revision = "d5e6f7a8b9c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # tables
    conn.execute(sa.text("ALTER TABLE tables DROP CONSTRAINT IF EXISTS tables_workspace_id_fkey"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_tables_workspace_id"))
    conn.execute(sa.text("ALTER TABLE tables DROP COLUMN IF EXISTS workspace_id"))
    conn.execute(sa.text("ALTER TABLE tables DROP CONSTRAINT IF EXISTS tables_persona_id_fkey"))
    op.alter_column("tables", "persona_id", nullable=False)
    conn.execute(sa.text("ALTER TABLE tables DROP CONSTRAINT IF EXISTS tables_persona_id_fkey"))
    op.create_foreign_key(
        "tables_persona_id_fkey", "tables", "personas",
        ["persona_id"], ["id"], ondelete="CASCADE",
    )
    # categories
    conn.execute(sa.text("ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_workspace_id_fkey"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_categories_workspace_id"))
    conn.execute(sa.text("ALTER TABLE categories DROP COLUMN IF EXISTS workspace_id"))
    conn.execute(sa.text("ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_persona_id_fkey"))
    op.alter_column("categories", "persona_id", nullable=False)
    conn.execute(sa.text("ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_persona_id_fkey"))
    op.create_foreign_key(
        "categories_persona_id_fkey", "categories", "personas",
        ["persona_id"], ["id"], ondelete="CASCADE",
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