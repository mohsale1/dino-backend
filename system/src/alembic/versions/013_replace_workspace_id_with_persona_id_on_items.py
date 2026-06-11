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

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add persona_id column (nullable first so existing rows don't violate NOT NULL)
    op.add_column(
        "items",
        sa.Column("persona_id", sa.BigInteger(), nullable=True),
    )

    # 2. Back-fill persona_id from the category each item belongs to
    op.execute(
        """
        UPDATE items
        SET persona_id = categories.persona_id
        FROM categories
        WHERE items.category_id = categories.id
        """
    )

    # 3. Make persona_id NOT NULL now that all rows are populated
    op.alter_column("items", "persona_id", nullable=False)

    # 4. Add FK constraint
    op.create_foreign_key(
        "items_persona_id_fkey",
        "items", "personas",
        ["persona_id"], ["id"],
        ondelete="CASCADE",
    )

    # 5. Add index
    op.create_index("ix_items_persona_id", "items", ["persona_id"])

    # 6. Drop workspace_id FK + index + column
    op.drop_constraint("items_workspace_id_fkey", "items", type_="foreignkey")
    op.drop_index("ix_items_workspace_id", table_name="items")
    op.drop_column("items", "workspace_id")


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
