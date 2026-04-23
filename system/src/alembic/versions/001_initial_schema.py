"""Initial schema - dino-system

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-04-22 00:00:00.000000

Creates ALL tables for the shared database in correct FK dependency order.
dino-system owns all DDL; dino-application reads from the same database.

Table creation order:
  1.  roles
  2.  permissions
  3.  role_permissions
  4.  workspaces
  5.  workspace_billing
  6.  personas
  7.  workspace_personas
  8.  users
  9.  customers
  10. areas
  11. tables
  12. categories
  13. items
  14. order_details
  15. orders
  16. order_transactions
  17. billing_details
  18. billing_transactions
  19. user_personas
  20. reviews
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NOW = sa.text("now()")


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. roles
    # ------------------------------------------------------------------
    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("role_type", sa.SmallInteger(), nullable=False, server_default="0",
                  comment="0=System, 1=Application"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )
    op.create_index("ix_roles_is_active", "roles", ["is_active"])
    op.create_index("ix_roles_role_type", "roles", ["role_type"])

    # ------------------------------------------------------------------
    # 2. permissions
    # ------------------------------------------------------------------
    op.create_table(
        "permissions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("category", sa.String(50), nullable=False, comment="system or application"),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.UniqueConstraint("category", "resource", "action",
                            name="uq_permissions_category_resource_action"),
    )
    op.create_index("ix_permissions_is_active", "permissions", ["is_active"])
    op.create_index("ix_permissions_category", "permissions", ["category"])
    op.create_index("ix_permissions_resource", "permissions", ["resource"])

    # ------------------------------------------------------------------
    # 3. role_permissions
    # ------------------------------------------------------------------
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.BigInteger(), nullable=False, primary_key=True),
        sa.Column("permission_id", sa.BigInteger(), nullable=False, primary_key=True),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"],
                                name="fk_role_permissions_role_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"],
                                name="fk_role_permissions_permission_id", ondelete="CASCADE"),
    )
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    # ------------------------------------------------------------------
    # 4. workspaces
    #    owner_id and referred_by are added as plain BigInteger columns here;
    #    FK to users is added after users table is created (step 8).
    # ------------------------------------------------------------------
    op.create_table(
        "workspaces",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.BigInteger(), nullable=True),
        sa.Column("referred_by", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
    )
    op.create_index("ix_workspaces_is_active", "workspaces", ["is_active"])

    # ------------------------------------------------------------------
    # 5. workspace_billing
    # ------------------------------------------------------------------
    op.create_table(
        "workspace_billing",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="'free'"),
        sa.Column("plan_status", sa.String(50), nullable=False, server_default="'active'"),
        sa.Column("billing_cycle", sa.String(20), nullable=True),
        sa.Column("billing_email", sa.String(320), nullable=True),
        sa.Column("billing_name", sa.String(200), nullable=True),
        sa.Column("billing_address", sa.Text(), nullable=True),
        sa.Column("billing_city", sa.String(100), nullable=True),
        sa.Column("billing_state", sa.String(100), nullable=True),
        sa.Column("billing_country", sa.String(100), nullable=True),
        sa.Column("billing_postal_code", sa.String(20), nullable=True),
        sa.Column("billing_phone", sa.String(30), nullable=True),
        sa.Column("next_billing_date", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"],
                                name="fk_workspace_billing_workspace_id", ondelete="CASCADE"),
        sa.UniqueConstraint("workspace_id", name="uq_workspace_billing_workspace_id"),
    )
    op.create_index("ix_workspace_billing_plan_status", "workspace_billing", ["plan_status"])
    op.create_index("ix_workspace_billing_next_billing_date", "workspace_billing", ["next_billing_date"])

    # ------------------------------------------------------------------
    # 6. personas
    # ------------------------------------------------------------------
    op.create_table(
        "personas",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("persona_type", sa.SmallInteger(), nullable=False, server_default="0",
                  comment="0=Food, 1=NonFood"),
        sa.Column("order_type", sa.SmallInteger(), nullable=False, server_default="0",
                  comment="0=Online, 1=Manual"),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_deactivated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"],
                                name="fk_personas_workspace_id", ondelete="CASCADE"),
    )
    op.create_index("ix_personas_is_active", "personas", ["is_active"])
    op.create_index("ix_personas_persona_type", "personas", ["persona_type"])
    op.create_index("ix_personas_workspace_id", "personas", ["workspace_id"])

    # ------------------------------------------------------------------
    # 7. workspace_personas
    # ------------------------------------------------------------------
    op.create_table(
        "workspace_personas",
        sa.Column("workspace_id", sa.BigInteger(), nullable=False, primary_key=True),
        sa.Column("persona_id", sa.BigInteger(), nullable=False, primary_key=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"],
                                name="fk_workspace_personas_workspace_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"],
                                name="fk_workspace_personas_persona_id", ondelete="CASCADE"),
    )
    op.create_index("ix_workspace_personas_persona_id", "workspace_personas", ["persona_id"])

    # ------------------------------------------------------------------
    # 8. users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("user_type", sa.SmallInteger(), nullable=False, server_default="0",
                  comment="0=System, 1=Application"),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("last_login", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"],
                                name="fk_users_role_id", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"],
                                name="fk_users_workspace_id", ondelete="CASCADE"),
        sa.UniqueConstraint("email", "workspace_id", name="uq_users_email_workspace"),
    )
    op.create_index("ix_users_is_active", "users", ["is_active"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_workspace_id", "users", ["workspace_id"])
    op.create_index("ix_users_user_type", "users", ["user_type"])
    op.create_index("ix_users_role_id", "users", ["role_id"])

    # Now add FK constraints on workspaces.owner_id and workspaces.referred_by
    op.create_foreign_key(
        "fk_workspaces_owner_id", "workspaces", "users",
        ["owner_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_workspaces_referred_by", "workspaces", "users",
        ["referred_by"], ["id"], ondelete="SET NULL",
    )

    # ------------------------------------------------------------------
    # 9. customers
    # ------------------------------------------------------------------
    op.create_table(
        "customers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("mobile", sa.String(30), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("persona_id", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"],
                                name="fk_customers_workspace_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"],
                                name="fk_customers_persona_id", ondelete="SET NULL"),
        sa.UniqueConstraint("mobile", "workspace_id", name="uq_customers_mobile_workspace"),
    )
    op.create_index("ix_customers_workspace_id", "customers", ["workspace_id"])
    op.create_index("ix_customers_is_active", "customers", ["is_active"])

    # ------------------------------------------------------------------
    # 10. areas
    # ------------------------------------------------------------------
    op.create_table(
        "areas",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("persona_id", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"],
                                name="fk_areas_workspace_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"],
                                name="fk_areas_persona_id", ondelete="SET NULL"),
    )
    op.create_index("ix_areas_workspace_id", "areas", ["workspace_id"])
    op.create_index("ix_areas_is_active", "areas", ["is_active"])

    # ------------------------------------------------------------------
    # 11. tables
    # ------------------------------------------------------------------
    op.create_table(
        "tables",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("table_number", sa.String(50), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("status", sa.String(30), nullable=False, server_default="'available'"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("area_id", sa.BigInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"],
                                name="fk_tables_workspace_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["area_id"], ["areas.id"],
                                name="fk_tables_area_id", ondelete="RESTRICT"),
        sa.UniqueConstraint("area_id", "table_number", name="uq_tables_area_table_number"),
    )
    op.create_index("ix_tables_workspace_id", "tables", ["workspace_id"])
    op.create_index("ix_tables_area_id", "tables", ["area_id"])
    op.create_index("ix_tables_is_active", "tables", ["is_active"])

    # ------------------------------------------------------------------
    # 12. categories
    # ------------------------------------------------------------------
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("persona_id", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"],
                                name="fk_categories_workspace_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"],
                                name="fk_categories_persona_id", ondelete="SET NULL"),
    )
    op.create_index("ix_categories_workspace_id", "categories", ["workspace_id"])
    op.create_index("ix_categories_is_active", "categories", ["is_active"])

    # ------------------------------------------------------------------
    # 13. items
    # ------------------------------------------------------------------
    op.create_table(
        "items",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_vegetarian", sa.Boolean(), nullable=True),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"],
                                name="fk_items_workspace_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"],
                                name="fk_items_category_id", ondelete="RESTRICT"),
    )
    op.create_index("ix_items_workspace_id", "items", ["workspace_id"])
    op.create_index("ix_items_category_id", "items", ["category_id"])
    op.create_index("ix_items_is_active", "items", ["is_active"])

    # ------------------------------------------------------------------
    # 14. order_details
    # ------------------------------------------------------------------
    op.create_table(
        "order_details",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("order_id", sa.String(50), nullable=False, unique=True),
        sa.Column("order_type", sa.String(30), nullable=False, server_default="'dine_in'"),
        sa.Column("status", sa.String(30), nullable=False, server_default="'pending'"),
        sa.Column("customer_id", sa.BigInteger(), nullable=True),
        sa.Column("customer_name", sa.String(200), nullable=False),
        sa.Column("table_id", sa.BigInteger(), nullable=True),
        sa.Column("area_id", sa.BigInteger(), nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("service_charge", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="'INR'"),
        sa.Column("special_instructions", sa.Text(), nullable=True),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("persona_id", sa.BigInteger(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"],
                                name="fk_order_details_customer_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"],
                                name="fk_order_details_table_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["area_id"], ["areas.id"],
                                name="fk_order_details_area_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"],
                                name="fk_order_details_workspace_id", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"],
                                name="fk_order_details_persona_id", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"],
                                name="fk_order_details_created_by", ondelete="SET NULL"),
    )
    op.create_index("ix_order_details_order_id", "order_details", ["order_id"])
    op.create_index("ix_order_details_workspace_id", "order_details", ["workspace_id"])
    op.create_index("ix_order_details_persona_id", "order_details", ["persona_id"])
    op.create_index("ix_order_details_status", "order_details", ["status"])
    op.create_index("ix_order_details_is_active", "order_details", ["is_active"])

    # ------------------------------------------------------------------
    # 15. orders  (line items — PK is sino, not id)
    # ------------------------------------------------------------------
    op.create_table(
        "orders",
        sa.Column("sino", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("order_id", sa.String(50), nullable=False),
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(10, 2), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("persona_id", sa.BigInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"],
                                name="fk_orders_workspace_id", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"],
                                name="fk_orders_persona_id", ondelete="RESTRICT"),
    )
    op.create_index("ix_orders_order_id", "orders", ["order_id"])
    op.create_index("ix_orders_workspace_id", "orders", ["workspace_id"])
    op.create_index("ix_orders_persona_id", "orders", ["persona_id"])
    op.create_index("ix_orders_item_id", "orders", ["item_id"])

    # ------------------------------------------------------------------
    # 16. order_transactions
    # ------------------------------------------------------------------
    op.create_table(
        "order_transactions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("order_id", sa.String(50), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=True),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("persona_id", sa.BigInteger(), nullable=False),
        sa.Column("paid_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="'INR'"),
        sa.Column("payment_method", sa.String(50), nullable=True),
        sa.Column("payment_status", sa.String(30), nullable=False, server_default="'unpaid'"),
        sa.Column("payment_ref", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"],
                                name="fk_order_transactions_customer_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"],
                                name="fk_order_transactions_workspace_id", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"],
                                name="fk_order_transactions_persona_id", ondelete="RESTRICT"),
    )
    op.create_index("ix_order_transactions_order_id", "order_transactions", ["order_id"])
    op.create_index("ix_order_transactions_workspace_id", "order_transactions", ["workspace_id"])

    # ------------------------------------------------------------------
    # 17. billing_details
    # ------------------------------------------------------------------
    op.create_table(
        "billing_details",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("legal_name", sa.String(200), nullable=True),
        sa.Column("trade_name", sa.String(200), nullable=True),
        sa.Column("gstin", sa.String(20), nullable=True),
        sa.Column("pan", sa.String(20), nullable=True),
        sa.Column("billing_email", sa.String(320), nullable=True),
        sa.Column("billing_phone", sa.String(30), nullable=True),
        sa.Column("address_line1", sa.String(300), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"],
                                name="fk_billing_details_workspace_id", ondelete="CASCADE"),
    )
    op.create_index("ix_billing_details_workspace_id", "billing_details", ["workspace_id"])

    # ------------------------------------------------------------------
    # 18. billing_transactions
    # ------------------------------------------------------------------
    op.create_table(
        "billing_transactions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="'INR'"),
        sa.Column("billing_period_start", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("billing_period_end", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("payment_status", sa.String(30), nullable=False, server_default="'pending'"),
        sa.Column("payment_method", sa.String(50), nullable=True),
        sa.Column("payment_ref", sa.String(200), nullable=True),
        sa.Column("invoice_number", sa.String(100), nullable=True, unique=True),
        sa.Column("last_paid_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("paid_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"],
                                name="fk_billing_transactions_workspace_id", ondelete="RESTRICT"),
    )
    op.create_index("ix_billing_transactions_workspace_id", "billing_transactions", ["workspace_id"])
    op.create_index("ix_billing_transactions_payment_status", "billing_transactions", ["payment_status"])

    # ------------------------------------------------------------------
    # 19. user_personas
    # ------------------------------------------------------------------
    op.create_table(
        "user_personas",
        sa.Column("user_id", sa.BigInteger(), nullable=False, primary_key=True),
        sa.Column("persona_id", sa.BigInteger(), nullable=False, primary_key=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],
                                name="fk_user_personas_user_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"],
                                name="fk_user_personas_persona_id", ondelete="CASCADE"),
    )
    op.create_index("ix_user_personas_persona_id", "user_personas", ["persona_id"])

    # ------------------------------------------------------------------
    # 20. reviews
    # ------------------------------------------------------------------
    op.create_table(
        "reviews",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("persona_id", sa.BigInteger(), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("rating", sa.SmallInteger(), nullable=False, server_default="5"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"],
                                name="fk_reviews_workspace_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"],
                                name="fk_reviews_persona_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],
                                name="fk_reviews_user_id", ondelete="SET NULL"),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating"),
    )
    op.create_index("ix_reviews_workspace_id", "reviews", ["workspace_id"])
    op.create_index("ix_reviews_persona_id", "reviews", ["persona_id"])
    op.create_index("ix_reviews_user_id", "reviews", ["user_id"])
    op.create_index("ix_reviews_is_approved", "reviews", ["is_approved"])
    op.create_index("ix_reviews_rating", "reviews", ["rating"])
    op.create_index("ix_reviews_is_active", "reviews", ["is_active"])


def downgrade() -> None:
    # Drop in reverse dependency order.
    # reviews has no dependents — drop it first.
    op.drop_index("ix_reviews_is_active", table_name="reviews")
    op.drop_index("ix_reviews_rating", table_name="reviews")
    op.drop_index("ix_reviews_is_approved", table_name="reviews")
    op.drop_index("ix_reviews_user_id", table_name="reviews")
    op.drop_index("ix_reviews_persona_id", table_name="reviews")
    op.drop_index("ix_reviews_workspace_id", table_name="reviews")
    op.drop_table("reviews")

    op.drop_table("user_personas")

    op.drop_index("ix_billing_transactions_payment_status", table_name="billing_transactions")
    op.drop_index("ix_billing_transactions_workspace_id", table_name="billing_transactions")
    op.drop_table("billing_transactions")

    op.drop_index("ix_billing_details_workspace_id", table_name="billing_details")
    op.drop_table("billing_details")

    op.drop_index("ix_order_transactions_workspace_id", table_name="order_transactions")
    op.drop_index("ix_order_transactions_order_id", table_name="order_transactions")
    op.drop_table("order_transactions")

    op.drop_index("ix_orders_item_id", table_name="orders")
    op.drop_index("ix_orders_persona_id", table_name="orders")
    op.drop_index("ix_orders_workspace_id", table_name="orders")
    op.drop_index("ix_orders_order_id", table_name="orders")
    op.drop_table("orders")

    op.drop_index("ix_order_details_is_active", table_name="order_details")
    op.drop_index("ix_order_details_status", table_name="order_details")
    op.drop_index("ix_order_details_persona_id", table_name="order_details")
    op.drop_index("ix_order_details_workspace_id", table_name="order_details")
    op.drop_index("ix_order_details_order_id", table_name="order_details")
    op.drop_table("order_details")

    op.drop_index("ix_items_is_active", table_name="items")
    op.drop_index("ix_items_category_id", table_name="items")
    op.drop_index("ix_items_workspace_id", table_name="items")
    op.drop_table("items")

    op.drop_index("ix_categories_is_active", table_name="categories")
    op.drop_index("ix_categories_workspace_id", table_name="categories")
    op.drop_table("categories")

    op.drop_index("ix_tables_is_active", table_name="tables")
    op.drop_index("ix_tables_area_id", table_name="tables")
    op.drop_index("ix_tables_workspace_id", table_name="tables")
    op.drop_table("tables")

    op.drop_index("ix_areas_is_active", table_name="areas")
    op.drop_index("ix_areas_workspace_id", table_name="areas")
    op.drop_table("areas")

    op.drop_index("ix_customers_is_active", table_name="customers")
    op.drop_index("ix_customers_workspace_id", table_name="customers")
    op.drop_table("customers")

    # Drop FK constraints on workspaces before dropping users
    op.drop_constraint("fk_workspaces_referred_by", "workspaces", type_="foreignkey")
    op.drop_constraint("fk_workspaces_owner_id", "workspaces", type_="foreignkey")

    op.drop_index("ix_users_role_id", table_name="users")
    op.drop_index("ix_users_user_type", table_name="users")
    op.drop_index("ix_users_workspace_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_workspace_personas_persona_id", table_name="workspace_personas")
    op.drop_table("workspace_personas")

    op.drop_index("ix_personas_workspace_id", table_name="personas")
    op.drop_index("ix_personas_persona_type", table_name="personas")
    op.drop_index("ix_personas_is_active", table_name="personas")
    op.drop_table("personas")

    op.drop_index("ix_workspace_billing_next_billing_date", table_name="workspace_billing")
    op.drop_index("ix_workspace_billing_plan_status", table_name="workspace_billing")
    op.drop_table("workspace_billing")

    op.drop_index("ix_workspaces_is_active", table_name="workspaces")
    op.drop_table("workspaces")

    op.drop_index("ix_role_permissions_permission_id", table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index("ix_permissions_resource", table_name="permissions")
    op.drop_index("ix_permissions_category", table_name="permissions")
    op.drop_index("ix_permissions_is_active", table_name="permissions")
    op.drop_table("permissions")

    op.drop_index("ix_roles_role_type", table_name="roles")
    op.drop_index("ix_roles_is_active", table_name="roles")
    op.drop_table("roles")
