"""Performance indexes — dino-application

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-19 00:00:00.000000

Audit findings cross-referenced against every repository and route in
dino-application.  Three categories of missing indexes are addressed:

  A. pg_trgm GIN indexes for ILIKE search columns
     -----------------------------------------------
     application_users: email, first_name, last_name
       -> UserRepository.get_paginated_users uses .ilike('%q%') across all three
     items: name, description
       -> ItemRepository.get_paginated_by_workspace uses .ilike('%q%') on both
          columns directly.  The existing ix_items_name_description_fts is a
          tsvector GIN index and is NOT used by ILIKE predicates.

  B. Composite indexes for high-cardinality filter combinations
     -----------------------------------------------------------
     Every paginated repository method scopes by workspace_id (or
     organization_id) AND guards against soft-deleted rows.  Single-column
     indexes on each column force PostgreSQL to intersect two bitmap scans;
     a composite index eliminates that overhead entirely.

     application_users : (workspace_id, is_deleted)
                         (organization_id, is_deleted)
     items             : (workspace_id, is_deleted)
                         (workspace_id, is_available) WHERE is_deleted = false
     categories        : (workspace_id, is_deleted)
                         (workspace_id, is_available) WHERE is_deleted = false
     areas             : (workspace_id, is_deleted)
                         (workspace_id, is_available) WHERE is_deleted = false
     tables            : (workspace_id, is_deleted)
                         (workspace_id, area_id)      WHERE is_deleted = false
                         (workspace_id, status)        WHERE is_deleted = false
     orders            : (workspace_id, is_deleted)
                         (organization_id, is_deleted)
                         (workspace_id, status)        WHERE is_deleted = false
                         (workspace_id, order_date)    WHERE is_deleted = false
     coupons           : (workspace_id, is_deleted)
                         (workspace_id, code)          WHERE is_deleted = false
                         (workspace_id, is_available)  WHERE is_deleted = false
     reviews           : (workspace_id, is_deleted)
                         (is_deleted, is_approved)
     organizations     : (workspace_id, is_deleted)

  C. Missing indexes on FK columns with no existing index
     ------------------------------------------------------
     reviews.created_by — FK fk_reviews_created_by exists; no index

     NOTE: orders.table_id and orders.area_id indexes are created in
     003_missing_columns.py alongside the columns they support — not here.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ======================================================================
    # A. pg_trgm GIN indexes for ILIKE search
    # ======================================================================

    # -- application_users: email (ILIKE in get_paginated_users) -----------
    op.create_index(
        "ix_application_users_email_trgm",
        "application_users",
        ["email"],
        postgresql_using="gin",
        postgresql_ops={"email": "gin_trgm_ops"},
    )

    # -- application_users: first_name (ILIKE in get_paginated_users) ------
    op.create_index(
        "ix_application_users_first_name_trgm",
        "application_users",
        ["first_name"],
        postgresql_using="gin",
        postgresql_ops={"first_name": "gin_trgm_ops"},
    )

    # -- application_users: last_name (ILIKE in get_paginated_users) -------
    op.create_index(
        "ix_application_users_last_name_trgm",
        "application_users",
        ["last_name"],
        postgresql_using="gin",
        postgresql_ops={"last_name": "gin_trgm_ops"},
    )

    # -- items: name (ILIKE in get_paginated_by_workspace) -----------------
    # Note: ix_items_name_description_fts is a tsvector GIN index and is
    # NOT consulted for ILIKE predicates.  A separate trgm index is required.
    op.create_index(
        "ix_items_name_trgm",
        "items",
        ["name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )

    # -- items: description (ILIKE in get_paginated_by_workspace) ----------
    op.create_index(
        "ix_items_description_trgm",
        "items",
        ["description"],
        postgresql_using="gin",
        postgresql_ops={"description": "gin_trgm_ops"},
    )

    # ======================================================================
    # B. Composite indexes for high-cardinality filter combinations
    # ======================================================================

    # -- application_users -------------------------------------------------

    # UserRepository.get_paginated_users: workspace_id + is_deleted
    op.create_index(
        "ix_application_users_workspace_id_is_deleted",
        "application_users",
        ["workspace_id", "is_deleted"],
    )

    # UserRepository.get_paginated_users: organization_id + is_deleted
    op.create_index(
        "ix_application_users_organization_id_is_deleted",
        "application_users",
        ["organization_id", "is_deleted"],
    )

    # -- items -------------------------------------------------------------

    # ItemRepository.get_paginated_by_workspace: workspace_id + is_deleted
    op.create_index(
        "ix_items_workspace_id_is_deleted",
        "items",
        ["workspace_id", "is_deleted"],
    )

    # ItemRepository.get_paginated_by_workspace: workspace_id + is_available
    # Partial: only active (non-deleted) rows are ever queried with is_available
    op.create_index(
        "ix_items_workspace_id_is_available",
        "items",
        ["workspace_id", "is_available"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # -- categories --------------------------------------------------------

    # CategoryRepository.get_paginated_by_workspace: workspace_id + is_deleted
    op.create_index(
        "ix_categories_workspace_id_is_deleted",
        "categories",
        ["workspace_id", "is_deleted"],
    )

    # CategoryRepository.get_paginated_by_workspace: workspace_id + is_available
    op.create_index(
        "ix_categories_workspace_id_is_available",
        "categories",
        ["workspace_id", "is_available"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # -- areas -------------------------------------------------------------

    # AreaRepository.get_paginated_by_workspace: workspace_id + is_deleted
    op.create_index(
        "ix_areas_workspace_id_is_deleted",
        "areas",
        ["workspace_id", "is_deleted"],
    )

    # AreaRepository.get_paginated_by_workspace: workspace_id + is_available
    op.create_index(
        "ix_areas_workspace_id_is_available",
        "areas",
        ["workspace_id", "is_available"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # -- tables ------------------------------------------------------------

    # TableRepository.get_paginated_by_workspace: workspace_id + is_deleted
    op.create_index(
        "ix_tables_workspace_id_is_deleted",
        "tables",
        ["workspace_id", "is_deleted"],
    )

    # TableRepository.get_paginated_by_workspace: workspace_id + area_id
    # Partial: area_id filter is only applied on non-deleted rows
    op.create_index(
        "ix_tables_workspace_id_area_id",
        "tables",
        ["workspace_id", "area_id"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # TableRepository.get_paginated_by_workspace: workspace_id + status
    # Partial: status filter is only applied on non-deleted rows
    op.create_index(
        "ix_tables_workspace_id_status",
        "tables",
        ["workspace_id", "status"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # -- orders ------------------------------------------------------------

    # OrderRepository: workspace_id + is_deleted (all workspace-scoped queries)
    op.create_index(
        "ix_orders_workspace_id_is_deleted",
        "orders",
        ["workspace_id", "is_deleted"],
    )

    # OrderRepository.get_paginated_by_organization: organization_id + is_deleted
    op.create_index(
        "ix_orders_organization_id_is_deleted",
        "orders",
        ["organization_id", "is_deleted"],
    )

    # OrderRepository: workspace_id + status filter (get_paginated_by_workspace
    # with filters={"status": ...})
    op.create_index(
        "ix_orders_workspace_id_status",
        "orders",
        ["workspace_id", "status"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # OrderRepository.get_orders_for_analytics: workspace_id + order_date
    # date-range predicates (order_date >= start, order_date <= end)
    op.create_index(
        "ix_orders_workspace_id_order_date",
        "orders",
        ["workspace_id", "order_date"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # -- coupons -----------------------------------------------------------

    # CouponRepository.get_by_workspace: workspace_id + is_deleted
    op.create_index(
        "ix_coupons_workspace_id_is_deleted",
        "coupons",
        ["workspace_id", "is_deleted"],
    )

    # CouponRepository.get_by_code: workspace_id + code lookup
    # Partial: get_by_code always excludes deleted rows by default
    op.create_index(
        "ix_coupons_workspace_id_code",
        "coupons",
        ["workspace_id", "code"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # CouponRepository.get_by_workspace with is_available filter
    op.create_index(
        "ix_coupons_workspace_id_is_available",
        "coupons",
        ["workspace_id", "is_available"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # -- reviews -----------------------------------------------------------

    # ReviewRepository.get_by_workspace: workspace_id + is_deleted
    op.create_index(
        "ix_reviews_workspace_id_is_deleted",
        "reviews",
        ["workspace_id", "is_deleted"],
    )

    # ReviewRepository.get_approved_reviews: global is_deleted + is_approved scan
    op.create_index(
        "ix_reviews_is_deleted_is_approved",
        "reviews",
        ["is_deleted", "is_approved"],
    )

    # -- organizations -----------------------------------------------------

    # OrganizationRepository.get_by_workspace: workspace_id + is_deleted
    op.create_index(
        "ix_organizations_workspace_id_is_deleted",
        "organizations",
        ["workspace_id", "is_deleted"],
    )

    # ======================================================================
    # C. Missing FK column indexes
    # ======================================================================

    # reviews.created_by — FK fk_reviews_created_by has no supporting index
    op.create_index(
        "ix_reviews_created_by",
        "reviews",
        ["created_by"],
    )

    # NOTE: ix_orders_table_id and ix_orders_area_id are created in
    # 003_missing_columns.py alongside the columns they support.


def downgrade() -> None:
    # ======================================================================
    # C. FK indexes
    # ======================================================================
    op.drop_index("ix_reviews_created_by", table_name="reviews")

    # ======================================================================
    # B. Composite indexes (reverse order of creation)
    # ======================================================================

    # organizations
    op.drop_index("ix_organizations_workspace_id_is_deleted", table_name="organizations")

    # reviews
    op.drop_index("ix_reviews_is_deleted_is_approved", table_name="reviews")
    op.drop_index("ix_reviews_workspace_id_is_deleted", table_name="reviews")

    # coupons
    op.drop_index("ix_coupons_workspace_id_is_available", table_name="coupons")
    op.drop_index("ix_coupons_workspace_id_code", table_name="coupons")
    op.drop_index("ix_coupons_workspace_id_is_deleted", table_name="coupons")

    # orders
    op.drop_index("ix_orders_workspace_id_order_date", table_name="orders")
    op.drop_index("ix_orders_workspace_id_status", table_name="orders")
    op.drop_index("ix_orders_organization_id_is_deleted", table_name="orders")
    op.drop_index("ix_orders_workspace_id_is_deleted", table_name="orders")

    # tables
    op.drop_index("ix_tables_workspace_id_status", table_name="tables")
    op.drop_index("ix_tables_workspace_id_area_id", table_name="tables")
    op.drop_index("ix_tables_workspace_id_is_deleted", table_name="tables")

    # areas
    op.drop_index("ix_areas_workspace_id_is_available", table_name="areas")
    op.drop_index("ix_areas_workspace_id_is_deleted", table_name="areas")

    # categories
    op.drop_index("ix_categories_workspace_id_is_available", table_name="categories")
    op.drop_index("ix_categories_workspace_id_is_deleted", table_name="categories")

    # items
    op.drop_index("ix_items_workspace_id_is_available", table_name="items")
    op.drop_index("ix_items_workspace_id_is_deleted", table_name="items")

    # application_users
    op.drop_index("ix_application_users_organization_id_is_deleted", table_name="application_users")
    op.drop_index("ix_application_users_workspace_id_is_deleted", table_name="application_users")

    # ======================================================================
    # A. pg_trgm GIN indexes
    # ======================================================================
    op.drop_index("ix_items_description_trgm", table_name="items")
    op.drop_index("ix_items_name_trgm", table_name="items")
    op.drop_index("ix_application_users_last_name_trgm", table_name="application_users")
    op.drop_index("ix_application_users_first_name_trgm", table_name="application_users")
    op.drop_index("ix_application_users_email_trgm", table_name="application_users")
