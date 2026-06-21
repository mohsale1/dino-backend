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

revision = "f7a8b9c0d1e3"
down_revision = "e6f7a8b9c0d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE customers DROP CONSTRAINT IF EXISTS uq_customers_mobile_workspace"))
    conn.execute(sa.text("ALTER TABLE customers DROP CONSTRAINT IF EXISTS customers_workspace_id_fkey"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_customers_workspace_id"))
    conn.execute(sa.text("ALTER TABLE customers DROP COLUMN IF EXISTS workspace_id"))
    conn.execute(sa.text("ALTER TABLE customers DROP CONSTRAINT IF EXISTS customers_persona_id_fkey"))
    conn.execute(sa.text("ALTER TABLE customers DROP COLUMN IF EXISTS persona_id"))
    conn.execute(sa.text("ALTER TABLE customers DROP CONSTRAINT IF EXISTS uq_customers_mobile"))
    op.create_unique_constraint("uq_customers_mobile", "customers", ["mobile"])
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_customers_mobile"))
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