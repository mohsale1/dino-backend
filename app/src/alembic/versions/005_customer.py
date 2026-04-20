"""Customer model — dino-application

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-20 00:00:00.000000

Summary of changes
==================
1.  Create table  customers
      - id            BIGINT PK autoincrement
      - name          VARCHAR(200) NOT NULL
      - mobile        VARCHAR(30)  NOT NULL
      - workspace_id  BIGINT NOT NULL FK→workspaces.id CASCADE
      - is_active     BOOLEAN NOT NULL DEFAULT true
      - created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
      - updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
2.  Create indexes on customers:
      ix_customers_workspace_id   (workspace_id)
      ix_customers_mobile         (mobile)
      ix_customers_workspace_mobile (workspace_id, mobile)  — composite lookup key
3.  Add column  orders.customer_id  BIGINT nullable FK→customers.id SET NULL
4.  Create index  ix_orders_customer_id  on orders(customer_id)
5.  Create FK constraint  fk_orders_customer_id

downgrade() reverses all steps in reverse order.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ==================================================================
    # 1. Create customers table
    # ==================================================================
    op.create_table(
        "customers",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("mobile", sa.String(30), nullable=False),
        sa.Column(
            "workspace_id",
            sa.BigInteger(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE", name="fk_customers_workspace_id"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ==================================================================
    # 2. Create indexes on customers
    # ==================================================================
    op.create_index("ix_customers_workspace_id", "customers", ["workspace_id"])
    op.create_index("ix_customers_mobile", "customers", ["mobile"])
    # Composite index — the primary lookup key: find customer by mobile within workspace
    op.create_index(
        "ix_customers_workspace_mobile",
        "customers",
        ["workspace_id", "mobile"],
    )

    # ==================================================================
    # 3. Add customer_id column to orders (nullable — historical orders
    #    without a customer link are preserved)
    # ==================================================================
    op.add_column(
        "orders",
        sa.Column(
            "customer_id",
            sa.BigInteger(),
            nullable=True,
        ),
    )

    # ==================================================================
    # 4. Create index on orders.customer_id
    # ==================================================================
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])

    # ==================================================================
    # 5. Create FK constraint: orders.customer_id → customers.id SET NULL
    # ==================================================================
    op.create_foreign_key(
        "fk_orders_customer_id",
        "orders",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="SET NULL",
    )


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # ==================================================================
    # 5 (reverse). Drop FK constraint fk_orders_customer_id
    # ==================================================================
    op.drop_constraint("fk_orders_customer_id", "orders", type_="foreignkey")

    # ==================================================================
    # 4 (reverse). Drop index ix_orders_customer_id
    # ==================================================================
    op.drop_index("ix_orders_customer_id", table_name="orders")

    # ==================================================================
    # 3 (reverse). Drop column orders.customer_id
    # ==================================================================
    op.drop_column("orders", "customer_id")

    # ==================================================================
    # 2 (reverse). Drop indexes on customers
    # ==================================================================
    op.drop_index("ix_customers_workspace_mobile", table_name="customers")
    op.drop_index("ix_customers_mobile", table_name="customers")
    op.drop_index("ix_customers_workspace_id", table_name="customers")

    # ==================================================================
    # 1 (reverse). Drop customers table
    #    (FK fk_customers_workspace_id is dropped implicitly with the table)
    # ==================================================================
    op.drop_table("customers")
