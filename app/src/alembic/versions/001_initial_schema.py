"""Initial schema - dino-application

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-04-19 00:00:00.000000

Creates all tables for the dino-application service in correct FK dependency order:
  1.  roles
  2.  permissions
  3.  role_permissions
  4.  workspaces
  5.  organizations
  6.  workspace_organizations
  7.  application_users
  8.  areas
  9.  categories
  10. items
  11. tables
  12. orders
  13. order_items
  14. coupons
  15. reviews
  16. homepage_info
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW_DEFAULT = sa.text("now()")


def upgrade() -> None:
    # ------------------------------------------------------------------
    # PostgreSQL extensions
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ------------------------------------------------------------------
    # 1. roles
    # ------------------------------------------------------------------
    op.create_table(
        "roles",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role_type", sa.SmallInteger(), nullable=False, server_default="1",
                  comment="0=System, 1=Application"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("permissions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
    )
    op.create_index("ix_roles_is_deleted", "roles", ["is_deleted"])
    op.create_index("ix_roles_role_type", "roles", ["role_type"])

    # ------------------------------------------------------------------
    # 2. permissions
    # ------------------------------------------------------------------
    op.create_table(
        "permissions",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("category", sa.String(50), nullable=False,
                  comment="system or application"),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
    )
    op.create_index("ix_permissions_is_deleted", "permissions", ["is_deleted"])
    # GIN index on name for pg_trgm full-text search
    op.create_index(
        "ix_permissions_name_trgm",
        "permissions",
        ["name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )

    # ------------------------------------------------------------------
    # 3. role_permissions  (junction: roles <-> permissions)
    #    Composite PK on (role_id, permission_id) — no separate id column.
    # ------------------------------------------------------------------
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.BigInteger(), nullable=False, primary_key=True),
        sa.Column("permission_id", sa.BigInteger(), nullable=False, primary_key=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name="fk_role_permissions_role_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name="fk_role_permissions_permission_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
    op.create_index(
        "ix_role_permissions_permission_id", "role_permissions", ["permission_id"]
    )

    # ------------------------------------------------------------------
    # 4. workspaces
    #    owner_id is String(4) — references system_users.id (4-digit code).
    #    referred_by is String(10) — soft cross-service reference.
    # ------------------------------------------------------------------
    op.create_table(
        "workspaces",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "owner_id",
            sa.String(4),
            nullable=True,
            comment="FK to system_users.id — 4-digit numeric referral code",
        ),
        # Billing fields
        sa.Column("billing_name", sa.String(200), nullable=True),
        sa.Column("billing_email", sa.String(255), nullable=True),
        sa.Column("billing_phone", sa.String(50), nullable=True),
        sa.Column("billing_address", sa.Text(), nullable=True),
        sa.Column("billing_city", sa.String(100), nullable=True),
        sa.Column("billing_state", sa.String(100), nullable=True),
        sa.Column("billing_postal_code", sa.String(20), nullable=True),
        sa.Column("billing_country", sa.String(100), nullable=True),
        # Subscription fields
        sa.Column("subscription_plan", sa.String(50), nullable=True, server_default="'Free'"),
        sa.Column("subscription_status", sa.String(50), nullable=True, server_default="'Active'"),
        sa.Column("next_billing_date", sa.TIMESTAMP(timezone=True), nullable=True),
        # Referral — stores the 4-digit system user ID string
        sa.Column("referred_by", sa.String(10), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
    )
    op.create_index("ix_workspaces_is_deleted", "workspaces", ["is_deleted"])
    op.create_index("ix_workspaces_owner_id", "workspaces", ["owner_id"])

    # ------------------------------------------------------------------
    # 5. organizations
    # ------------------------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_type", sa.SmallInteger(), nullable=False,
                  server_default="0", comment="0=FOOD, 1=NON_FOOD"),
        sa.Column("order_type", sa.SmallInteger(), nullable=False,
                  server_default="0", comment="0=Online, 1=Manual/Counter"),
        # Contact / address
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        # Operational state
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default="true"),
        # JSONB settings blob
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_organizations_workspace_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_organizations_workspace_id", "organizations", ["workspace_id"])
    op.create_index("ix_organizations_is_deleted", "organizations", ["is_deleted"])

    # ------------------------------------------------------------------
    # 6. workspace_organizations  (junction: workspaces <-> organizations)
    #    Composite PK on (workspace_id, organization_id) — no separate id column.
    # ------------------------------------------------------------------
    op.create_table(
        "workspace_organizations",
        sa.Column("workspace_id", sa.BigInteger(), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), nullable=False, primary_key=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_workspace_organizations_workspace_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_workspace_organizations_organization_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_workspace_organizations_workspace_id",
        "workspace_organizations",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_organizations_organization_id",
        "workspace_organizations",
        ["organization_id"],
    )

    # ------------------------------------------------------------------
    # 7. application_users
    # ------------------------------------------------------------------
    op.create_table(
        "application_users",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=True),
        sa.Column("last_login", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name="fk_application_users_role_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_application_users_workspace_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_application_users_organization_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_application_users_email", "application_users", ["email"]
    )
    op.create_index(
        "ix_application_users_workspace_id", "application_users", ["workspace_id"]
    )
    op.create_index(
        "ix_application_users_organization_id", "application_users", ["organization_id"]
    )
    op.create_index(
        "ix_application_users_role_id", "application_users", ["role_id"]
    )
    op.create_index(
        "ix_application_users_is_deleted", "application_users", ["is_deleted"]
    )

    # workspaces.owner_id is String(4) — no FK constraint enforced here
    # (cross-service soft reference to system_users.id)

    # ------------------------------------------------------------------
    # 8. areas
    # ------------------------------------------------------------------
    op.create_table(
        "areas",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_areas_workspace_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_areas_organization_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_areas_workspace_id", "areas", ["workspace_id"])
    op.create_index("ix_areas_organization_id", "areas", ["organization_id"])
    op.create_index("ix_areas_is_deleted", "areas", ["is_deleted"])

    # ------------------------------------------------------------------
    # 9. categories  (self-referential parent_id)
    # ------------------------------------------------------------------
    op.create_table(
        "categories",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=True),
        sa.Column("parent_id", sa.BigInteger(), nullable=True,
                  comment="Self-referential parent category"),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_categories_workspace_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_categories_organization_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["categories.id"],
            name="fk_categories_parent_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_categories_workspace_id", "categories", ["workspace_id"])
    op.create_index("ix_categories_organization_id", "categories", ["organization_id"])
    op.create_index("ix_categories_is_deleted", "categories", ["is_deleted"])
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"])

    # ------------------------------------------------------------------
    # 10. items
    # ------------------------------------------------------------------
    op.create_table(
        "items",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_vegetarian", sa.Boolean(), nullable=True,
                  comment="True=Veg, False=Non-Veg, NULL=Not Applicable"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_items_category_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_items_workspace_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_items_workspace_id", "items", ["workspace_id"])
    op.create_index("ix_items_category_id", "items", ["category_id"])
    op.create_index("ix_items_is_deleted", "items", ["is_deleted"])
    # GIN index on (name, description) for full-text search
    op.execute(
        """
        CREATE INDEX ix_items_name_description_fts
        ON items
        USING gin(
            to_tsvector('english', coalesce(name, '') || ' ' || coalesce(description, ''))
        )
        """
    )

    # ------------------------------------------------------------------
    # 11. tables
    # ------------------------------------------------------------------
    op.create_table(
        "tables",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("table_number", sa.String(50), nullable=False),
        sa.Column("area_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=True),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("status", sa.String(50), nullable=False, server_default="'available'",
                  comment="available, occupied, reserved, maintenance"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.ForeignKeyConstraint(
            ["area_id"],
            ["areas.id"],
            name="fk_tables_area_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_tables_organization_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_tables_workspace_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_tables_workspace_id", "tables", ["workspace_id"])
    op.create_index("ix_tables_organization_id", "tables", ["organization_id"])
    op.create_index("ix_tables_area_id", "tables", ["area_id"])
    op.create_index("ix_tables_status", "tables", ["status"])
    op.create_index("ix_tables_is_deleted", "tables", ["is_deleted"])

    # ------------------------------------------------------------------
    # 12. orders
    # ------------------------------------------------------------------
    op.create_table(
        "orders",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("order_number", sa.String(50), nullable=False, unique=True),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("table_id", sa.BigInteger(), nullable=True),
        sa.Column("area_id", sa.BigInteger(), nullable=True),
        # Customer info
        sa.Column("customer_name", sa.String(200), nullable=False),
        sa.Column("customer_email", sa.String(255), nullable=True),
        sa.Column("customer_phone", sa.String(50), nullable=True),
        # Financials
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="'USD'"),
        # Status
        sa.Column("status", sa.String(50), nullable=False, server_default="'pending'",
                  comment="pending, confirmed, preparing, ready, delivered, cancelled"),
        sa.Column("payment_status", sa.String(50), nullable=False, server_default="'unpaid'",
                  comment="unpaid, paid, refunded, partial"),
        # Shipping / notes
        sa.Column("shipping_address", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("order_date", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=_NOW_DEFAULT),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_orders_workspace_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_orders_organization_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["table_id"],
            ["tables.id"],
            name="fk_orders_table_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["area_id"],
            ["areas.id"],
            name="fk_orders_area_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_orders_workspace_id", "orders", ["workspace_id"])
    op.create_index("ix_orders_organization_id", "orders", ["organization_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_is_deleted", "orders", ["is_deleted"])
    op.create_index("ix_orders_order_date", "orders", ["order_date"])

    # ------------------------------------------------------------------
    # 13. order_items
    # ------------------------------------------------------------------
    op.create_table(
        "order_items",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.String(255), nullable=False,
                  comment="Item ID (string to support legacy IDs)"),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name="fk_order_items_order_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    # ------------------------------------------------------------------
    # 14. coupons
    # ------------------------------------------------------------------
    op.create_table(
        "coupons",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("discount_type", sa.String(20), nullable=False,
                  comment="percentage or fixed"),
        sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("max_discount_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("min_order_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("usage_limit_per_user", sa.Integer(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_from", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("valid_until", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.UniqueConstraint("code", "workspace_id", name="uq_coupons_code_workspace"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_coupons_workspace_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_coupons_workspace_id", "coupons", ["workspace_id"])
    op.create_index("ix_coupons_is_deleted", "coupons", ["is_deleted"])

    # ------------------------------------------------------------------
    # 15. reviews
    # ------------------------------------------------------------------
    op.create_table(
        "reviews",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("customer_name", sa.String(200), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("restaurant", sa.String(200), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("avatar", sa.String(255), nullable=True),
        sa.Column("workspace_id", sa.BigInteger(), nullable=True),
        sa.Column("organization_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_reviews_workspace_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_reviews_organization_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["application_users.id"],
            name="fk_reviews_created_by",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_reviews_workspace_id", "reviews", ["workspace_id"])
    op.create_index("ix_reviews_organization_id", "reviews", ["organization_id"])
    op.create_index("ix_reviews_is_deleted", "reviews", ["is_deleted"])
    op.create_index("ix_reviews_is_approved", "reviews", ["is_approved"])

    # ------------------------------------------------------------------
    # 16. homepage_info
    # ------------------------------------------------------------------
    op.create_table(
        "homepage_info",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("stats", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("testimonials", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("contact", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
    )
    op.create_index("ix_homepage_info_is_deleted", "homepage_info", ["is_deleted"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("homepage_info")
    op.drop_table("reviews")
    op.drop_table("coupons")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("tables")
    op.drop_table("items")
    op.drop_table("categories")
    op.drop_table("areas")
    op.drop_table("application_users")
    op.drop_table("workspace_organizations")
    op.drop_table("organizations")
    op.drop_table("workspaces")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
