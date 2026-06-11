"""012_refactor_customers

Revision ID: 012
Revises: 011
Create Date: 2026-05-16

Changes:
- Drop workspace_id (column, FK, index) from customers
- Drop persona_id (column, FK, index) from customers
- Drop old unique constraint uq_customers_mobile_workspace
- Add new unique constraint uq_customers_mobile (mobile globally unique)
"""

import sqlalchemy as sa
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop old composite unique constraint (mobile, workspace_id)
    op.drop_constraint("uq_customers_mobile_workspace", "customers", type_="unique")

    # 2. Drop workspace_id FK + index + column
    op.drop_constraint("customers_workspace_id_fkey", "customers", type_="foreignkey")
    op.drop_index("ix_customers_workspace_id", table_name="customers")
    op.drop_column("customers", "workspace_id")

    # 3. Drop persona_id FK + column (no dedicated index existed)
    op.drop_constraint("customers_persona_id_fkey", "customers", type_="foreignkey")
    op.drop_column("customers", "persona_id")

    # 4. Add global unique constraint on mobile
    op.create_unique_constraint("uq_customers_mobile", "customers", ["mobile"])

    # 5. Add index on mobile for fast lookups
    op.create_index("ix_customers_mobile", "customers", ["mobile"])


def downgrade() -> None:
    # 1. Drop new unique constraint + index
    op.drop_index("ix_customers_mobile", table_name="customers")
    op.drop_constraint("uq_customers_mobile", "customers", type_="unique")

    # 2. Re-add persona_id column + FK
    op.add_column("customers", sa.Column("persona_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "customers_persona_id_fkey",
        "customers", "personas",
        ["persona_id"], ["id"],
        ondelete="SET NULL",
    )

    # 3. Re-add workspace_id column + FK + index
    op.add_column("customers", sa.Column("workspace_id", sa.BigInteger(), nullable=False))
    op.create_foreign_key(
        "customers_workspace_id_fkey",
        "customers", "workspaces",
        ["workspace_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_customers_workspace_id", "customers", ["workspace_id"])

    # 4. Restore old composite unique constraint
    op.create_unique_constraint(
        "uq_customers_mobile_workspace", "customers", ["mobile", "workspace_id"]
    )
