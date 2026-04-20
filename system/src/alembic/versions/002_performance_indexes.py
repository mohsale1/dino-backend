"""Performance indexes — dino-system

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-19 00:00:00.000000

Audit findings cross-referenced against every repository in dino-system.
Three categories of missing indexes are addressed:

  A. pg_trgm GIN indexes for ILIKE search columns
     -----------------------------------------------
     system_users: email, first_name, last_name
       -> UserRepository.get_paginated_users uses .ilike('%q%') across all
          three columns in an OR predicate.  Without trgm indexes PostgreSQL
          falls back to a sequential scan for every search request.

  B. Composite indexes for high-cardinality filter combinations
     -----------------------------------------------------------
     workspaces        : (is_deleted, is_active)
                           get_paginated_workspaces filters both columns.
                         (is_deleted, subscription_plan)
                           get_paginated_workspaces optionally filters
                           subscription_plan on top of the is_deleted guard.
     organizations     : (workspace_id, is_deleted)
                           get_by_workspace always filters both columns.
     registration_codes: (workspace_id, is_deleted)
                           standard scoped soft-delete pattern used by every
                           paginated query on this table.

     NOTE: ix_system_users_is_deleted_role_id was intentionally omitted —
     system_users has NO is_deleted column (only is_active), so a composite
     index on (is_deleted, role_id) would be invalid.

  C. Missing indexes omitted from migration 001
     ------------------------------------------------------
     No unindexed FK columns were found in dino-system beyond those already
     covered by the initial migration (ix_registration_codes_workspace_id,
     ix_workspace_organizations_workspace_id, ix_system_users_role_id, etc.).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ======================================================================
    # A. pg_trgm GIN indexes for ILIKE search
    # ======================================================================

    # -- system_users: email (ILIKE in get_paginated_users) ----------------
    op.create_index(
        "ix_system_users_email_trgm",
        "system_users",
        ["email"],
        postgresql_using="gin",
        postgresql_ops={"email": "gin_trgm_ops"},
    )

    # -- system_users: first_name (ILIKE in get_paginated_users) -----------
    op.create_index(
        "ix_system_users_first_name_trgm",
        "system_users",
        ["first_name"],
        postgresql_using="gin",
        postgresql_ops={"first_name": "gin_trgm_ops"},
    )

    # -- system_users: last_name (ILIKE in get_paginated_users) ------------
    op.create_index(
        "ix_system_users_last_name_trgm",
        "system_users",
        ["last_name"],
        postgresql_using="gin",
        postgresql_ops={"last_name": "gin_trgm_ops"},
    )

    # ======================================================================
    # B. Composite indexes for high-cardinality filter combinations
    # ======================================================================

    # -- workspaces --------------------------------------------------------

    # Missing from migration 001: subscription_status single-column index
    # (present in Workspace.__table_args__ but omitted from the initial migration)
    op.create_index(
        "ix_workspaces_subscription_status",
        "workspaces",
        ["subscription_status"],
    )

    # WorkspaceRepository.get_paginated_workspaces: is_deleted + is_active
    op.create_index(
        "ix_workspaces_is_deleted_is_active",
        "workspaces",
        ["is_deleted", "is_active"],
    )

    # WorkspaceRepository.get_paginated_workspaces: is_deleted + subscription_plan
    # Partial: subscription_plan filter is only meaningful on non-deleted rows
    op.create_index(
        "ix_workspaces_is_deleted_subscription_plan",
        "workspaces",
        ["is_deleted", "subscription_plan"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # -- organizations -----------------------------------------------------

    # OrganizationRepository.get_by_workspace: workspace_id + is_deleted
    op.create_index(
        "ix_organizations_workspace_id_is_deleted",
        "organizations",
        ["workspace_id", "is_deleted"],
    )

    # -- registration_codes ------------------------------------------------

    # Standard scoped soft-delete pattern: workspace_id + is_deleted
    op.create_index(
        "ix_registration_codes_workspace_id_is_deleted",
        "registration_codes",
        ["workspace_id", "is_deleted"],
    )


def downgrade() -> None:
    # ======================================================================
    # B. Composite indexes (reverse order of creation)
    # ======================================================================

    # registration_codes
    op.drop_index(
        "ix_registration_codes_workspace_id_is_deleted",
        table_name="registration_codes",
    )

    # organizations
    op.drop_index(
        "ix_organizations_workspace_id_is_deleted",
        table_name="organizations",
    )

    # workspaces
    op.drop_index(
        "ix_workspaces_is_deleted_subscription_plan",
        table_name="workspaces",
    )
    op.drop_index(
        "ix_workspaces_is_deleted_is_active",
        table_name="workspaces",
    )
    op.drop_index(
        "ix_workspaces_subscription_status",
        table_name="workspaces",
    )

    # ======================================================================
    # A. pg_trgm GIN indexes
    # ======================================================================
    op.drop_index("ix_system_users_last_name_trgm", table_name="system_users")
    op.drop_index("ix_system_users_first_name_trgm", table_name="system_users")
    op.drop_index("ix_system_users_email_trgm", table_name="system_users")
