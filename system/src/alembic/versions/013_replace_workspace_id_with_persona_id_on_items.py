"""013_replace_workspace_id_with_persona_id_on_items

Revision ID: 013
Revises: 012
Create Date: 2026-05-16

Changes:
- items: drop workspace_id (column, FK, index)
- items: add persona_id (BigInt, NOT NULL, FK→personas.id CASCADE)
- items: add index ix_items_persona_id
"""

import sqlalchemy as sa
from alembic import op

revision = "a8b9c0d1e2f4"
down_revision = "f7a8b9c0d1e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Add persona_id if not exists
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='items' AND column_name='persona_id'
            ) THEN
                ALTER TABLE items ADD COLUMN persona_id BIGINT;
            END IF;
        END $$;
    """))
    # Back-fill
    conn.execute(sa.text("""
        UPDATE items SET persona_id = categories.persona_id
        FROM categories WHERE items.category_id = categories.id
        AND items.persona_id IS NULL
    """))
    op.alter_column("items", "persona_id", nullable=False)
    conn.execute(sa.text("ALTER TABLE items DROP CONSTRAINT IF EXISTS items_persona_id_fkey"))
    op.create_foreign_key(
        "items_persona_id_fkey", "items", "personas",
        ["persona_id"], ["id"], ondelete="CASCADE",
    )
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_items_persona_id"))
    op.create_index("ix_items_persona_id", "items", ["persona_id"])
    # Drop workspace_id if exists
    conn.execute(sa.text("ALTER TABLE items DROP CONSTRAINT IF EXISTS items_workspace_id_fkey"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_items_workspace_id"))
    conn.execute(sa.text("ALTER TABLE items DROP COLUMN IF EXISTS workspace_id"))

def downgrade() -> None:
    # 1. Re-add workspace_id column (nullable first)
    op.add_column(
        "items",
        sa.Column("workspace_id", sa.BigInteger(), nullable=True),
    )

    # 2. Back-fill workspace_id from persona
    op.execute(
        """
        UPDATE items
        SET workspace_id = personas.workspace_id
        FROM personas
        WHERE items.persona_id = personas.id
        """
    )

    # 3. Make NOT NULL
    op.alter_column("items", "workspace_id", nullable=False)

    # 4. Restore FK + index
    op.create_foreign_key(
        "items_workspace_id_fkey",
        "items", "workspaces",
        ["workspace_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_items_workspace_id", "items", ["workspace_id"])

    # 5. Drop persona_id FK + index + column
    op.drop_constraint("items_persona_id_fkey", "items", type_="foreignkey")
    op.drop_index("ix_items_persona_id", table_name="items")
    op.drop_column("items", "persona_id")
