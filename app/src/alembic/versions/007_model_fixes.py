"""Model fixes — constraints, indexes, types, audit columns

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-20 00:00:00.000000

Summary of changes
==================
1.  application_users
      - Drop global UNIQUE on email; add composite UNIQUE (email, workspace_id)
      - Extend password_hash column to VARCHAR(512)

2.  roles
      - Add UNIQUE constraint on name

3.  role_permissions
      - Add index on permission_id (reverse lookup)

4.  orders
      - Drop global UNIQUE on order_number; add composite UNIQUE (order_number, workspace_id)

5.  order_items
      - Add created_at TIMESTAMPTZ NOT NULL DEFAULT now()
      - Add updated_at TIMESTAMPTZ NOT NULL DEFAULT now()

6.  tables
      - Add UNIQUE constraint (area_id, table_number)

7.  customers
      - Add UNIQUE constraint (mobile, workspace_id)

8.  workspace_billing
      - Add created_at TIMESTAMPTZ NOT NULL DEFAULT now()

9.  Remove duplicate indexes that were created by both index=True on the column
    AND an explicit Index() in __table_args__:
      - ix_personas_workspace_id (duplicate of auto-index from index=True)
      - ix_application_users_workspace_id (duplicate)
      - ix_orders_workspace_id, ix_orders_persona_id, ix_orders_table_id,
        ix_orders_area_id, ix_orders_customer_id (all duplicates)
      - ix_areas_workspace_id, ix_areas_persona_id (duplicates; replaced by composite)
      - ix_tables_workspace_id, ix_tables_area_id (duplicates)
      - ix_categories_workspace_id, ix_categories_parent_id (duplicates)
      - ix_items_workspace_id, ix_items_category_id (duplicates)
      - ix_reviews_workspace_id, ix_reviews_persona_id (duplicates)
      - ix_coupons_workspace_id (duplicate)
      - ix_workspace_billing_workspace_id (duplicate of unique constraint index)
      - ix_workspaces_owner_id (duplicate)

10. Add composite index ix_areas_workspace_persona (workspace_id, persona_id)

downgrade() reverses all steps in reverse order.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ==================================================================
    # 1. application_users — email uniqueness scope + password length
    # ==================================================================
    # Drop global unique constraint on email
    op.drop_constraint("application_users_email_key", "application_users", type_="unique")
    # Add workspace-scoped unique constraint
    op.create_unique_constraint(
        "uq_application_users_email_workspace",
        "application_users",
        ["email", "workspace_id"],
    )
    # Extend password_hash to 512 chars
    op.alter_column(
        "application_users",
        "password_hash",
        type_=sa.String(512),
        existing_nullable=False,
    )

    # ==================================================================
    # 2. roles — unique name
    # ==================================================================
    op.create_unique_constraint("uq_roles_name", "roles", ["name"])

    # ==================================================================
    # 3. role_permissions — reverse lookup index
    # ==================================================================
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    # ==================================================================
    # 4. orders — workspace-scoped order_number uniqueness
    # ==================================================================
    op.drop_constraint("orders_order_number_key", "orders", type_="unique")
    op.create_unique_constraint(
        "uq_orders_order_number_workspace",
        "orders",
        ["order_number", "workspace_id"],
    )

    # ==================================================================
    # 5. order_items — add audit timestamps
    # ==================================================================
    op.add_column(
        "order_items",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "order_items",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ==================================================================
    # 6. tables — unique table_number within area
    # ==================================================================
    op.create_unique_constraint(
        "uq_tables_area_table_number",
        "tables",
        ["area_id", "table_number"],
    )

    # ==================================================================
    # 7. customers — unique mobile within workspace
    # ==================================================================
    op.create_unique_constraint(
        "uq_customers_mobile_workspace",
        "customers",
        ["mobile", "workspace_id"],
    )

    # ==================================================================
    # 8. workspace_billing — add created_at
    # ==================================================================
    op.add_column(
        "workspace_billing",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ==================================================================
    # 9. Drop duplicate indexes (safe — use IF EXISTS via raw SQL)
    # ==================================================================
    duplicate_indexes = [
        "ix_personas_workspace_id",
        "ix_application_users_workspace_id",
        "ix_orders_workspace_id",
        "ix_orders_persona_id",
        "ix_orders_table_id",
        "ix_orders_area_id",
        "ix_orders_customer_id",
        "ix_areas_workspace_id",
        "ix_areas_persona_id",
        "ix_tables_workspace_id",
        "ix_tables_area_id",
        "ix_categories_workspace_id",
        "ix_categories_parent_id",
        "ix_items_workspace_id",
        "ix_items_category_id",
        "ix_reviews_workspace_id",
        "ix_reviews_persona_id",
        "ix_coupons_workspace_id",
        "ix_workspace_billing_workspace_id",
        "ix_workspaces_owner_id",
    ]
    for idx in duplicate_indexes:
        op.execute(f"DROP INDEX IF EXISTS {idx}")

    # ==================================================================
    # 10. Add composite index on areas
    # ==================================================================
    op.create_index("ix_areas_workspace_persona", "areas", ["workspace_id", "persona_id"])


def downgrade() -> None:

    # 10 (reverse)
    op.drop_index("ix_areas_workspace_persona", table_name="areas")

    # 9 (reverse) — recreate the dropped duplicate indexes
    op.create_index("ix_personas_workspace_id", "personas", ["workspace_id"])
    op.create_index("ix_application_users_workspace_id", "application_users", ["workspace_id"])
    op.create_index("ix_orders_workspace_id", "orders", ["workspace_id"])
    op.create_index("ix_orders_persona_id", "orders", ["persona_id"])
    op.create_index("ix_orders_table_id", "orders", ["table_id"])
    op.create_index("ix_orders_area_id", "orders", ["area_id"])
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_areas_workspace_id", "areas", ["workspace_id"])
    op.create_index("ix_areas_persona_id", "areas", ["persona_id"])
    op.create_index("ix_tables_workspace_id", "tables", ["workspace_id"])
    op.create_index("ix_tables_area_id", "tables", ["area_id"])
    op.create_index("ix_categories_workspace_id", "categories", ["workspace_id"])
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"])
    op.create_index("ix_items_workspace_id", "items", ["workspace_id"])
    op.create_index("ix_items_category_id", "items", ["category_id"])
    op.create_index("ix_reviews_workspace_id", "reviews", ["workspace_id"])
    op.create_index("ix_reviews_persona_id", "reviews", ["persona_id"])
    op.create_index("ix_coupons_workspace_id", "coupons", ["workspace_id"])
    op.create_index("ix_workspace_billing_workspace_id", "workspace_billing", ["workspace_id"])
    op.create_index("ix_workspaces_owner_id", "workspaces", ["owner_id"])

    # 8 (reverse)
    op.drop_column("workspace_billing", "created_at")

    # 7 (reverse)
    op.drop_constraint("uq_customers_mobile_workspace", "customers", type_="unique")

    # 6 (reverse)
    op.drop_constraint("uq_tables_area_table_number", "tables", type_="unique")

    # 5 (reverse)
    op.drop_column("order_items", "updated_at")
    op.drop_column("order_items", "created_at")

    # 4 (reverse)
    op.drop_constraint("uq_orders_order_number_workspace", "orders", type_="unique")
    op.create_unique_constraint("orders_order_number_key", "orders", ["order_number"])

    # 3 (reverse)
    op.drop_index("ix_role_permissions_permission_id", table_name="role_permissions")

    # 2 (reverse)
    op.drop_constraint("uq_roles_name", "roles", type_="unique")

    # 1 (reverse)
    op.alter_column(
        "application_users",
        "password_hash",
        type_=sa.String(255),
        existing_nullable=False,
    )
    op.drop_constraint("uq_application_users_email_workspace", "application_users", type_="unique")
    op.create_unique_constraint("application_users_email_key", "application_users", ["email"])
