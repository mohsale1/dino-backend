"""Persona rename — dino-application

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-20 00:00:00.000000

Summary of changes
==================
1.  Rename table  organizations          → personas
2.  Add column    personas.is_deactivated  BOOLEAN NOT NULL DEFAULT false
3.  Rename column organization_id → persona_id in:
      application_users, areas, orders, tables, categories, reviews
4.  Rename table  workspace_organizations → workspace_personas
5.  Rename column organization_id → persona_id in workspace_personas
6.  Drop soft-delete columns (is_deleted, deleted_at, restored_at) from every
    table that carries them:
      personas, workspaces, application_users, areas, orders, tables,
      categories, items, roles, permissions, coupons, reviews, homepage_info
    order_items never had these columns — skipped.
7.  Drop every index that references is_deleted (simple + composite + partial).
    IMPORTANT: indexes are dropped BEFORE the columns they reference, so that
    PostgreSQL does not error on dropping a column that still has a dependent
    index.
8.  Create new index ix_personas_is_active on personas(is_active).
9.  Rename FK constraints: fk_*_organization_id → fk_*_persona_id.
10. Rename indexes:         ix_*_organization_id → ix_*_persona_id.

downgrade() reverses all steps in reverse order.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ==================================================================
    # 1. Rename table organizations → personas
    # ==================================================================
    op.rename_table("organizations", "personas")

    # ==================================================================
    # 2. Add is_deactivated to personas
    # ==================================================================
    op.add_column(
        "personas",
        sa.Column(
            "is_deactivated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="True = billing suspension; distinct from is_active (soft-delete)",
        ),
    )

    # ==================================================================
    # 3. Rename organization_id → persona_id in child tables
    #    Order: application_users, areas, orders, tables, categories, reviews
    #
    #    Each rename is done via alter_column with new_column_name.
    #    FK constraints that reference the old column name are handled in
    #    step 9 (drop old FK, create new FK with new name).
    # ==================================================================

    # -- application_users -----------------------------------------------
    op.alter_column(
        "application_users",
        "organization_id",
        new_column_name="persona_id",
    )

    # -- areas -----------------------------------------------------------
    op.alter_column(
        "areas",
        "organization_id",
        new_column_name="persona_id",
    )

    # -- orders ----------------------------------------------------------
    op.alter_column(
        "orders",
        "organization_id",
        new_column_name="persona_id",
    )

    # -- tables ----------------------------------------------------------
    op.alter_column(
        "tables",
        "organization_id",
        new_column_name="persona_id",
    )

    # -- categories ------------------------------------------------------
    op.alter_column(
        "categories",
        "organization_id",
        new_column_name="persona_id",
    )

    # -- reviews ---------------------------------------------------------
    op.alter_column(
        "reviews",
        "organization_id",
        new_column_name="persona_id",
    )

    # ==================================================================
    # 4. Rename table workspace_organizations → workspace_personas
    # ==================================================================
    op.rename_table("workspace_organizations", "workspace_personas")

    # ==================================================================
    # 5. Rename organization_id → persona_id in workspace_personas
    # ==================================================================
    op.alter_column(
        "workspace_personas",
        "organization_id",
        new_column_name="persona_id",
    )

    # ==================================================================
    # 7. Drop all indexes that reference is_deleted
    #
    #    MUST happen BEFORE step 6 (dropping the is_deleted columns),
    #    because PostgreSQL will refuse to drop a column that still has
    #    a dependent index.
    #
    #    Simple is_deleted indexes (from 001_initial_schema):
    #      ix_roles_is_deleted
    #      ix_permissions_is_deleted
    #      ix_workspaces_is_deleted
    #      ix_organizations_is_deleted          (table now: personas)
    #      ix_application_users_is_deleted
    #      ix_areas_is_deleted
    #      ix_categories_is_deleted
    #      ix_items_is_deleted
    #      ix_tables_is_deleted
    #      ix_orders_is_deleted
    #      ix_coupons_is_deleted
    #      ix_reviews_is_deleted
    #      ix_homepage_info_is_deleted
    #
    #    Composite indexes containing is_deleted (from 002_performance_indexes):
    #      ix_application_users_workspace_id_is_deleted
    #      ix_application_users_organization_id_is_deleted
    #      ix_items_workspace_id_is_deleted
    #      ix_categories_workspace_id_is_deleted
    #      ix_areas_workspace_id_is_deleted
    #      ix_tables_workspace_id_is_deleted
    #      ix_orders_workspace_id_is_deleted
    #      ix_orders_organization_id_is_deleted
    #      ix_coupons_workspace_id_is_deleted
    #      ix_reviews_workspace_id_is_deleted
    #      ix_organizations_workspace_id_is_deleted  (table now: personas)
    #      ix_reviews_is_deleted_is_approved
    #
    #    Partial indexes with WHERE is_deleted = false (from 002):
    #      ix_items_workspace_id_is_available
    #      ix_categories_workspace_id_is_available
    #      ix_areas_workspace_id_is_available
    #      ix_tables_workspace_id_area_id
    #      ix_tables_workspace_id_status
    #      ix_orders_workspace_id_status
    #      ix_orders_workspace_id_order_date
    #      ix_coupons_workspace_id_code
    #      ix_coupons_workspace_id_is_available
    # ==================================================================

    # Simple is_deleted indexes (001)
    op.drop_index("ix_roles_is_deleted", table_name="roles")
    op.drop_index("ix_permissions_is_deleted", table_name="permissions")
    op.drop_index("ix_workspaces_is_deleted", table_name="workspaces")
    # ix_organizations_is_deleted was on the organizations table, now personas
    op.drop_index("ix_organizations_is_deleted", table_name="personas")
    op.drop_index("ix_application_users_is_deleted", table_name="application_users")
    op.drop_index("ix_areas_is_deleted", table_name="areas")
    op.drop_index("ix_categories_is_deleted", table_name="categories")
    op.drop_index("ix_items_is_deleted", table_name="items")
    op.drop_index("ix_tables_is_deleted", table_name="tables")
    op.drop_index("ix_orders_is_deleted", table_name="orders")
    op.drop_index("ix_coupons_is_deleted", table_name="coupons")
    op.drop_index("ix_reviews_is_deleted", table_name="reviews")
    op.drop_index("ix_homepage_info_is_deleted", table_name="homepage_info")

    # Composite is_deleted indexes (002)
    op.drop_index("ix_application_users_workspace_id_is_deleted", table_name="application_users")
    op.drop_index("ix_application_users_organization_id_is_deleted", table_name="application_users")
    op.drop_index("ix_items_workspace_id_is_deleted", table_name="items")
    op.drop_index("ix_categories_workspace_id_is_deleted", table_name="categories")
    op.drop_index("ix_areas_workspace_id_is_deleted", table_name="areas")
    op.drop_index("ix_tables_workspace_id_is_deleted", table_name="tables")
    op.drop_index("ix_orders_workspace_id_is_deleted", table_name="orders")
    op.drop_index("ix_orders_organization_id_is_deleted", table_name="orders")
    op.drop_index("ix_coupons_workspace_id_is_deleted", table_name="coupons")
    op.drop_index("ix_reviews_workspace_id_is_deleted", table_name="reviews")
    op.drop_index("ix_organizations_workspace_id_is_deleted", table_name="personas")
    op.drop_index("ix_reviews_is_deleted_is_approved", table_name="reviews")

    # Partial indexes with WHERE is_deleted = false (002)
    op.drop_index("ix_items_workspace_id_is_available", table_name="items")
    op.drop_index("ix_categories_workspace_id_is_available", table_name="categories")
    op.drop_index("ix_areas_workspace_id_is_available", table_name="areas")
    op.drop_index("ix_tables_workspace_id_area_id", table_name="tables")
    op.drop_index("ix_tables_workspace_id_status", table_name="tables")
    op.drop_index("ix_orders_workspace_id_status", table_name="orders")
    op.drop_index("ix_orders_workspace_id_order_date", table_name="orders")
    op.drop_index("ix_coupons_workspace_id_code", table_name="coupons")
    op.drop_index("ix_coupons_workspace_id_is_available", table_name="coupons")

    # ==================================================================
    # 6. Drop soft-delete columns from all applicable tables
    #
    #    Indexes referencing is_deleted were already dropped above (step 7),
    #    so these column drops will succeed without constraint errors.
    #
    #    Tables with is_deleted / deleted_at / restored_at (from 001):
    #      roles, permissions, workspaces, personas (was organizations),
    #      application_users, areas, categories, items, tables, orders,
    #      coupons, reviews, homepage_info
    #
    #    Tables WITHOUT these columns (never created):
    #      role_permissions, workspace_personas (was workspace_organizations),
    #      order_items
    # ==================================================================

    # -- personas (was organizations) ------------------------------------
    op.drop_column("personas", "is_deleted")
    op.drop_column("personas", "deleted_at")
    op.drop_column("personas", "restored_at")

    # -- workspaces ------------------------------------------------------
    op.drop_column("workspaces", "is_deleted")
    op.drop_column("workspaces", "deleted_at")
    op.drop_column("workspaces", "restored_at")

    # -- application_users -----------------------------------------------
    op.drop_column("application_users", "is_deleted")
    op.drop_column("application_users", "deleted_at")
    op.drop_column("application_users", "restored_at")

    # -- areas -----------------------------------------------------------
    op.drop_column("areas", "is_deleted")
    op.drop_column("areas", "deleted_at")
    op.drop_column("areas", "restored_at")

    # -- orders ----------------------------------------------------------
    op.drop_column("orders", "is_deleted")
    op.drop_column("orders", "deleted_at")
    op.drop_column("orders", "restored_at")

    # -- tables ----------------------------------------------------------
    op.drop_column("tables", "is_deleted")
    op.drop_column("tables", "deleted_at")
    op.drop_column("tables", "restored_at")

    # -- categories ------------------------------------------------------
    op.drop_column("categories", "is_deleted")
    op.drop_column("categories", "deleted_at")
    op.drop_column("categories", "restored_at")

    # -- items -----------------------------------------------------------
    op.drop_column("items", "is_deleted")
    op.drop_column("items", "deleted_at")
    op.drop_column("items", "restored_at")

    # -- roles -----------------------------------------------------------
    op.drop_column("roles", "is_deleted")
    op.drop_column("roles", "deleted_at")
    op.drop_column("roles", "restored_at")

    # -- permissions -----------------------------------------------------
    op.drop_column("permissions", "is_deleted")
    op.drop_column("permissions", "deleted_at")
    op.drop_column("permissions", "restored_at")

    # -- coupons ---------------------------------------------------------
    op.drop_column("coupons", "is_deleted")
    op.drop_column("coupons", "deleted_at")
    op.drop_column("coupons", "restored_at")

    # -- reviews ---------------------------------------------------------
    op.drop_column("reviews", "is_deleted")
    op.drop_column("reviews", "deleted_at")
    op.drop_column("reviews", "restored_at")

    # -- homepage_info ---------------------------------------------------
    op.drop_column("homepage_info", "is_deleted")
    op.drop_column("homepage_info", "deleted_at")
    op.drop_column("homepage_info", "restored_at")

    # ==================================================================
    # 8. Create new index ix_personas_is_active on personas(is_active)
    # ==================================================================
    op.create_index("ix_personas_is_active", "personas", ["is_active"])

    # ==================================================================
    # 9. Rename FK constraints: fk_*_organization_id → fk_*_persona_id
    #
    #    Pattern: drop old FK, recreate with new name pointing at personas.
    #
    #    Affected FKs (from 001_initial_schema):
    #      fk_application_users_organization_id  → fk_application_users_persona_id
    #      fk_areas_organization_id              → fk_areas_persona_id
    #      fk_categories_organization_id         → fk_categories_persona_id
    #      fk_tables_organization_id             → fk_tables_persona_id
    #      fk_orders_organization_id             → fk_orders_persona_id
    #      fk_reviews_organization_id            → fk_reviews_persona_id
    #      fk_workspace_organizations_organization_id → fk_workspace_personas_persona_id
    #
    #    Also rename the organizations table FK on personas itself:
    #      fk_organizations_workspace_id stays as-is (references workspaces, not org)
    #      — no rename needed for that one.
    #
    #    workspace_organizations FK on workspace_id also renamed for table rename:
    #      fk_workspace_organizations_workspace_id → fk_workspace_personas_workspace_id
    # ==================================================================

    # -- application_users.persona_id → personas.id ----------------------
    op.drop_constraint(
        "fk_application_users_organization_id",
        "application_users",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_application_users_persona_id",
        "application_users",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -- areas.persona_id → personas.id ----------------------------------
    op.drop_constraint(
        "fk_areas_organization_id",
        "areas",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_areas_persona_id",
        "areas",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -- categories.persona_id → personas.id -----------------------------
    op.drop_constraint(
        "fk_categories_organization_id",
        "categories",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_categories_persona_id",
        "categories",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -- tables.persona_id → personas.id ---------------------------------
    op.drop_constraint(
        "fk_tables_organization_id",
        "tables",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_tables_persona_id",
        "tables",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -- orders.persona_id → personas.id ---------------------------------
    op.drop_constraint(
        "fk_orders_organization_id",
        "orders",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_orders_persona_id",
        "orders",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # -- reviews.persona_id → personas.id --------------------------------
    op.drop_constraint(
        "fk_reviews_organization_id",
        "reviews",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_reviews_persona_id",
        "reviews",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -- workspace_personas: rename both FKs for the table rename --------
    # workspace_id FK: old name referenced old table name in constraint name
    op.drop_constraint(
        "fk_workspace_organizations_workspace_id",
        "workspace_personas",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_workspace_personas_workspace_id",
        "workspace_personas",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # persona_id FK (was organization_id)
    op.drop_constraint(
        "fk_workspace_organizations_organization_id",
        "workspace_personas",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_workspace_personas_persona_id",
        "workspace_personas",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # -- personas table itself: rename its workspace FK constraint -------
    op.drop_constraint(
        "fk_organizations_workspace_id",
        "personas",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_personas_workspace_id",
        "personas",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ==================================================================
    # 10. Rename indexes: ix_*_organization_id → ix_*_persona_id
    #
    #     Simple organization_id indexes (from 001):
    #       ix_application_users_organization_id
    #       ix_areas_organization_id
    #       ix_categories_organization_id
    #       ix_tables_organization_id
    #       ix_orders_organization_id
    #       ix_reviews_organization_id
    #       ix_workspace_organizations_organization_id  (table: workspace_personas)
    #       ix_workspace_organizations_workspace_id     (table: workspace_personas)
    #       ix_organizations_workspace_id               (table: personas)
    #
    #     PostgreSQL does not have a native RENAME INDEX in Alembic's op API,
    #     so we drop and recreate each index.
    # ==================================================================

    # -- application_users -----------------------------------------------
    op.drop_index("ix_application_users_organization_id", table_name="application_users")
    op.create_index("ix_application_users_persona_id", "application_users", ["persona_id"])

    # -- areas -----------------------------------------------------------
    op.drop_index("ix_areas_organization_id", table_name="areas")
    op.create_index("ix_areas_persona_id", "areas", ["persona_id"])

    # -- categories ------------------------------------------------------
    op.drop_index("ix_categories_organization_id", table_name="categories")
    op.create_index("ix_categories_persona_id", "categories", ["persona_id"])

    # -- tables ----------------------------------------------------------
    op.drop_index("ix_tables_organization_id", table_name="tables")
    op.create_index("ix_tables_persona_id", "tables", ["persona_id"])

    # -- orders ----------------------------------------------------------
    op.drop_index("ix_orders_organization_id", table_name="orders")
    op.create_index("ix_orders_persona_id", "orders", ["persona_id"])

    # -- reviews ---------------------------------------------------------
    op.drop_index("ix_reviews_organization_id", table_name="reviews")
    op.create_index("ix_reviews_persona_id", "reviews", ["persona_id"])

    # -- workspace_personas (was workspace_organizations) ----------------
    op.drop_index(
        "ix_workspace_organizations_organization_id",
        table_name="workspace_personas",
    )
    op.create_index(
        "ix_workspace_personas_persona_id",
        "workspace_personas",
        ["persona_id"],
    )

    op.drop_index(
        "ix_workspace_organizations_workspace_id",
        table_name="workspace_personas",
    )
    op.create_index(
        "ix_workspace_personas_workspace_id",
        "workspace_personas",
        ["workspace_id"],
    )

    # -- personas (was organizations) workspace_id index -----------------
    op.drop_index("ix_organizations_workspace_id", table_name="personas")
    op.create_index("ix_personas_workspace_id", "personas", ["workspace_id"])


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # ==================================================================
    # 10 (reverse). Restore original organization_id index names
    # ==================================================================

    # -- personas workspace_id index -------------------------------------
    op.drop_index("ix_personas_workspace_id", table_name="personas")
    op.create_index("ix_organizations_workspace_id", "personas", ["workspace_id"])

    # -- workspace_personas (restore workspace_organizations names) ------
    op.drop_index("ix_workspace_personas_workspace_id", table_name="workspace_personas")
    op.create_index(
        "ix_workspace_organizations_workspace_id",
        "workspace_personas",
        ["workspace_id"],
    )

    op.drop_index("ix_workspace_personas_persona_id", table_name="workspace_personas")
    op.create_index(
        "ix_workspace_organizations_organization_id",
        "workspace_personas",
        ["persona_id"],
    )

    # -- reviews ---------------------------------------------------------
    op.drop_index("ix_reviews_persona_id", table_name="reviews")
    op.create_index("ix_reviews_organization_id", "reviews", ["persona_id"])

    # -- orders ----------------------------------------------------------
    op.drop_index("ix_orders_persona_id", table_name="orders")
    op.create_index("ix_orders_organization_id", "orders", ["persona_id"])

    # -- tables ----------------------------------------------------------
    op.drop_index("ix_tables_persona_id", table_name="tables")
    op.create_index("ix_tables_organization_id", "tables", ["persona_id"])

    # -- categories ------------------------------------------------------
    op.drop_index("ix_categories_persona_id", table_name="categories")
    op.create_index("ix_categories_organization_id", "categories", ["persona_id"])

    # -- areas -----------------------------------------------------------
    op.drop_index("ix_areas_persona_id", table_name="areas")
    op.create_index("ix_areas_organization_id", "areas", ["persona_id"])

    # -- application_users -----------------------------------------------
    op.drop_index("ix_application_users_persona_id", table_name="application_users")
    op.create_index(
        "ix_application_users_organization_id",
        "application_users",
        ["persona_id"],
    )

    # ==================================================================
    # 9 (reverse). Restore original FK constraint names
    # ==================================================================

    # -- personas workspace FK -------------------------------------------
    op.drop_constraint("fk_personas_workspace_id", "personas", type_="foreignkey")
    op.create_foreign_key(
        "fk_organizations_workspace_id",
        "personas",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # -- workspace_personas FKs ------------------------------------------
    op.drop_constraint(
        "fk_workspace_personas_persona_id",
        "workspace_personas",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_workspace_organizations_organization_id",
        "workspace_personas",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "fk_workspace_personas_workspace_id",
        "workspace_personas",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_workspace_organizations_workspace_id",
        "workspace_personas",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # -- reviews ---------------------------------------------------------
    op.drop_constraint("fk_reviews_persona_id", "reviews", type_="foreignkey")
    op.create_foreign_key(
        "fk_reviews_organization_id",
        "reviews",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -- orders ----------------------------------------------------------
    op.drop_constraint("fk_orders_persona_id", "orders", type_="foreignkey")
    op.create_foreign_key(
        "fk_orders_organization_id",
        "orders",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # -- tables ----------------------------------------------------------
    op.drop_constraint("fk_tables_persona_id", "tables", type_="foreignkey")
    op.create_foreign_key(
        "fk_tables_organization_id",
        "tables",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -- categories ------------------------------------------------------
    op.drop_constraint("fk_categories_persona_id", "categories", type_="foreignkey")
    op.create_foreign_key(
        "fk_categories_organization_id",
        "categories",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -- areas -----------------------------------------------------------
    op.drop_constraint("fk_areas_persona_id", "areas", type_="foreignkey")
    op.create_foreign_key(
        "fk_areas_organization_id",
        "areas",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -- application_users -----------------------------------------------
    op.drop_constraint(
        "fk_application_users_persona_id",
        "application_users",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_application_users_organization_id",
        "application_users",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ==================================================================
    # 8 (reverse). Drop ix_personas_is_active
    # ==================================================================
    op.drop_index("ix_personas_is_active", table_name="personas")

    # ==================================================================
    # 6 (reverse). Restore soft-delete columns
    #
    #    Columns are added FIRST (step 6 reverse), then indexes are
    #    recreated on them (step 7 reverse) — the inverse of upgrade order.
    # ==================================================================

    # -- homepage_info ---------------------------------------------------
    op.add_column(
        "homepage_info",
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "homepage_info",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "homepage_info",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # -- reviews ---------------------------------------------------------
    op.add_column(
        "reviews",
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "reviews",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "reviews",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # -- coupons ---------------------------------------------------------
    op.add_column(
        "coupons",
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "coupons",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "coupons",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # -- permissions -----------------------------------------------------
    op.add_column(
        "permissions",
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "permissions",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "permissions",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # -- roles -----------------------------------------------------------
    op.add_column(
        "roles",
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "roles",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "roles",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # -- items -----------------------------------------------------------
    op.add_column(
        "items",
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "items",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "items",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # -- categories ------------------------------------------------------
    op.add_column(
        "categories",
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "categories",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "categories",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # -- tables ----------------------------------------------------------
    op.add_column(
        "tables",
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "tables",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "tables",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # -- orders ----------------------------------------------------------
    op.add_column(
        "orders",
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # -- areas -----------------------------------------------------------
    op.add_column(
        "areas",
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "areas",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "areas",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # -- application_users -----------------------------------------------
    op.add_column(
        "application_users",
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "application_users",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "application_users",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # -- workspaces ------------------------------------------------------
    op.add_column(
        "workspaces",
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # -- personas (was organizations) ------------------------------------
    op.add_column(
        "personas",
        sa.Column("restored_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "personas",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "personas",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # ==================================================================
    # 7 (reverse). Recreate all is_deleted indexes
    #
    #    Columns exist again (added above), so indexes can be created.
    # ==================================================================

    # Partial indexes with WHERE is_deleted = false (002)
    op.create_index(
        "ix_coupons_workspace_id_is_available",
        "coupons",
        ["workspace_id", "is_available"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "ix_coupons_workspace_id_code",
        "coupons",
        ["workspace_id", "code"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "ix_orders_workspace_id_order_date",
        "orders",
        ["workspace_id", "order_date"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "ix_orders_workspace_id_status",
        "orders",
        ["workspace_id", "status"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "ix_tables_workspace_id_status",
        "tables",
        ["workspace_id", "status"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "ix_tables_workspace_id_area_id",
        "tables",
        ["workspace_id", "area_id"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "ix_areas_workspace_id_is_available",
        "areas",
        ["workspace_id", "is_available"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "ix_categories_workspace_id_is_available",
        "categories",
        ["workspace_id", "is_available"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "ix_items_workspace_id_is_available",
        "items",
        ["workspace_id", "is_available"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # Composite is_deleted indexes (002)
    op.create_index(
        "ix_reviews_is_deleted_is_approved",
        "reviews",
        ["is_deleted", "is_approved"],
    )
    op.create_index(
        "ix_organizations_workspace_id_is_deleted",
        "personas",
        ["workspace_id", "is_deleted"],
    )
    op.create_index(
        "ix_reviews_workspace_id_is_deleted",
        "reviews",
        ["workspace_id", "is_deleted"],
    )
    op.create_index(
        "ix_coupons_workspace_id_is_deleted",
        "coupons",
        ["workspace_id", "is_deleted"],
    )
    op.create_index(
        "ix_orders_organization_id_is_deleted",
        "orders",
        ["persona_id", "is_deleted"],
    )
    op.create_index(
        "ix_orders_workspace_id_is_deleted",
        "orders",
        ["workspace_id", "is_deleted"],
    )
    op.create_index(
        "ix_tables_workspace_id_is_deleted",
        "tables",
        ["workspace_id", "is_deleted"],
    )
    op.create_index(
        "ix_areas_workspace_id_is_deleted",
        "areas",
        ["workspace_id", "is_deleted"],
    )
    op.create_index(
        "ix_categories_workspace_id_is_deleted",
        "categories",
        ["workspace_id", "is_deleted"],
    )
    op.create_index(
        "ix_items_workspace_id_is_deleted",
        "items",
        ["workspace_id", "is_deleted"],
    )
    op.create_index(
        "ix_application_users_organization_id_is_deleted",
        "application_users",
        ["persona_id", "is_deleted"],
    )
    op.create_index(
        "ix_application_users_workspace_id_is_deleted",
        "application_users",
        ["workspace_id", "is_deleted"],
    )

    # Simple is_deleted indexes (001)
    op.create_index("ix_homepage_info_is_deleted", "homepage_info", ["is_deleted"])
    op.create_index("ix_reviews_is_deleted", "reviews", ["is_deleted"])
    op.create_index("ix_coupons_is_deleted", "coupons", ["is_deleted"])
    op.create_index("ix_orders_is_deleted", "orders", ["is_deleted"])
    op.create_index("ix_tables_is_deleted", "tables", ["is_deleted"])
    op.create_index("ix_items_is_deleted", "items", ["is_deleted"])
    op.create_index("ix_categories_is_deleted", "categories", ["is_deleted"])
    op.create_index("ix_areas_is_deleted", "areas", ["is_deleted"])
    op.create_index("ix_application_users_is_deleted", "application_users", ["is_deleted"])
    op.create_index("ix_organizations_is_deleted", "personas", ["is_deleted"])
    op.create_index("ix_workspaces_is_deleted", "workspaces", ["is_deleted"])
    op.create_index("ix_permissions_is_deleted", "permissions", ["is_deleted"])
    op.create_index("ix_roles_is_deleted", "roles", ["is_deleted"])

    # ==================================================================
    # 5 (reverse). Rename persona_id → organization_id in workspace_personas
    # ==================================================================
    op.alter_column(
        "workspace_personas",
        "persona_id",
        new_column_name="organization_id",
    )

    # ==================================================================
    # 4 (reverse). Rename table workspace_personas → workspace_organizations
    # ==================================================================
    op.rename_table("workspace_personas", "workspace_organizations")

    # ==================================================================
    # 3 (reverse). Rename persona_id → organization_id in child tables
    # ==================================================================
    op.alter_column("reviews", "persona_id", new_column_name="organization_id")
    op.alter_column("categories", "persona_id", new_column_name="organization_id")
    op.alter_column("tables", "persona_id", new_column_name="organization_id")
    op.alter_column("orders", "persona_id", new_column_name="organization_id")
    op.alter_column("areas", "persona_id", new_column_name="organization_id")
    op.alter_column("application_users", "persona_id", new_column_name="organization_id")

    # ==================================================================
    # 2 (reverse). Drop is_deactivated from personas
    # ==================================================================
    op.drop_column("personas", "is_deactivated")

    # ==================================================================
    # 1 (reverse). Rename table personas → organizations
    # ==================================================================
    op.rename_table("personas", "organizations")
