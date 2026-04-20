"""Persona rename — dino-system

Revision ID: b8c9d0e1f2a3
Revises: c3d4e5f6a7b8
Create Date: 2026-04-20 00:00:00.000000

Summary of changes
==================
1.  Drop table registration_codes (indexes and FK first).
2.  Rename table  organizations          → personas
3.  Add column    personas.is_deactivated  BOOLEAN NOT NULL DEFAULT false
4.  Rename table  workspace_organizations → workspace_personas
5.  Rename column organization_id → persona_id in workspace_personas
6.  Drop soft-delete columns (is_deleted, deleted_at, restored_at) from every
    table that carries them:
      personas, workspaces, roles, permissions, homepage_info
    system_users has NO is_deleted column — skipped.
    role_permissions and workspace_personas never had these columns — skipped.
7.  Drop every index that references is_deleted (simple + composite).
    IMPORTANT: indexes are dropped BEFORE the columns they reference, so that
    PostgreSQL does not error on dropping a column that still has a dependent
    index.
8.  Create new index ix_personas_is_active on personas(is_active).

downgrade() reverses all steps in reverse order, recreating registration_codes
last (since it depends on workspaces which must exist first).

Notes on dino-system specifics
================================
- organizations in dino-system has NO enforced FK to workspaces (cross-service
  reference stored as plain BigInteger) — no FK constraint to rename on personas.
- workspace_organizations.organization_id has NO enforced FK (cross-service
  reference) — only the workspace_id FK needs renaming for the table rename.
- system_users has NO is_deleted column (only is_active) — no columns to drop
  and no is_deleted indexes to drop for that table.
- ix_system_users_is_deleted_role_id was never validly created (system_users
  has no is_deleted column); it is dropped with IF EXISTS safety in upgrade
  and is NOT recreated in downgrade.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_NOW_DEFAULT = sa.text("now()")


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ==================================================================
    # 1. Drop table registration_codes
    #
    #    Indexes and FK must be dropped before the table itself.
    #    Indexes from 001: ix_registration_codes_workspace_id,
    #                      ix_registration_codes_is_deleted,
    #                      ix_registration_codes_code
    #    Composite index from 002: ix_registration_codes_workspace_id_is_deleted
    #    FK from 001: fk_registration_codes_workspace_id
    # ==================================================================
    op.drop_index(
        "ix_registration_codes_workspace_id_is_deleted",
        table_name="registration_codes",
    )
    op.drop_index(
        "ix_registration_codes_is_deleted",
        table_name="registration_codes",
    )
    op.drop_index(
        "ix_registration_codes_code",
        table_name="registration_codes",
    )
    op.drop_index(
        "ix_registration_codes_workspace_id",
        table_name="registration_codes",
    )
    op.drop_constraint(
        "fk_registration_codes_workspace_id",
        "registration_codes",
        type_="foreignkey",
    )
    op.drop_table("registration_codes")

    # ==================================================================
    # 2. Rename table organizations → personas
    # ==================================================================
    op.rename_table("organizations", "personas")

    # ==================================================================
    # 3. Add is_deactivated to personas
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
    # 4. Rename table workspace_organizations → workspace_personas
    # ==================================================================
    op.rename_table("workspace_organizations", "workspace_personas")

    # ==================================================================
    # 5. Rename organization_id → persona_id in workspace_personas
    #
    #    In dino-system, organization_id in workspace_organizations has
    #    NO enforced FK (cross-service reference), so no FK constraint
    #    needs to be dropped/recreated for this column rename.
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
    #      ix_homepage_info_is_deleted
    #      (ix_registration_codes_is_deleted already dropped in step 1)
    #
    #    Composite / partial indexes containing is_deleted (from 002):
    #      ix_workspaces_is_deleted_is_active
    #      ix_workspaces_is_deleted_subscription_plan
    #      ix_organizations_workspace_id_is_deleted  (table now: personas)
    #      (ix_registration_codes_workspace_id_is_deleted dropped in step 1)
    #
    #    ix_system_users_is_deleted_role_id: system_users has no is_deleted
    #    column so this index was never validly created in 002. Drop it with
    #    IF EXISTS to be safe without erroring if it does not exist.
    # ==================================================================

    # Simple is_deleted indexes (001)
    op.drop_index("ix_roles_is_deleted", table_name="roles")
    op.drop_index("ix_permissions_is_deleted", table_name="permissions")
    op.drop_index("ix_workspaces_is_deleted", table_name="workspaces")
    # ix_organizations_is_deleted was on organizations, now personas
    op.drop_index("ix_organizations_is_deleted", table_name="personas")
    op.drop_index("ix_homepage_info_is_deleted", table_name="homepage_info")

    # Composite / partial is_deleted indexes (002)
    # Use IF EXISTS for ix_system_users_is_deleted_role_id since system_users
    # has no is_deleted column and the index may not actually exist.
    op.execute("DROP INDEX IF EXISTS ix_system_users_is_deleted_role_id")
    op.drop_index("ix_workspaces_is_deleted_is_active", table_name="workspaces")
    op.drop_index(
        "ix_workspaces_is_deleted_subscription_plan",
        table_name="workspaces",
    )
    op.drop_index(
        "ix_organizations_workspace_id_is_deleted",
        table_name="personas",
    )

    # ==================================================================
    # 6. Drop soft-delete columns from all applicable tables
    #
    #    Indexes referencing is_deleted were already dropped above (step 7),
    #    so these column drops will succeed without constraint errors.
    #
    #    Tables with is_deleted / deleted_at / restored_at (from 001):
    #      roles, permissions, workspaces, personas (was organizations),
    #      homepage_info, registration_codes (already dropped in step 1)
    #
    #    Tables WITHOUT these columns:
    #      system_users        — only has is_active (no is_deleted)
    #      role_permissions    — junction table, no soft-delete columns
    #      workspace_personas  — junction table, no soft-delete columns
    # ==================================================================

    # -- personas (was organizations) ------------------------------------
    op.drop_column("personas", "is_deleted")
    op.drop_column("personas", "deleted_at")
    op.drop_column("personas", "restored_at")

    # -- workspaces ------------------------------------------------------
    op.drop_column("workspaces", "is_deleted")
    op.drop_column("workspaces", "deleted_at")
    op.drop_column("workspaces", "restored_at")

    # -- roles -----------------------------------------------------------
    op.drop_column("roles", "is_deleted")
    op.drop_column("roles", "deleted_at")
    op.drop_column("roles", "restored_at")

    # -- permissions -----------------------------------------------------
    op.drop_column("permissions", "is_deleted")
    op.drop_column("permissions", "deleted_at")
    op.drop_column("permissions", "restored_at")

    # -- homepage_info ---------------------------------------------------
    op.drop_column("homepage_info", "is_deleted")
    op.drop_column("homepage_info", "deleted_at")
    op.drop_column("homepage_info", "restored_at")

    # ==================================================================
    # 8. Create new index ix_personas_is_active on personas(is_active)
    # ==================================================================
    op.create_index("ix_personas_is_active", "personas", ["is_active"])

    # ==================================================================
    # Rename workspace_organizations FK on workspace_id for table rename
    #
    #    The workspace_id FK in workspace_organizations (now workspace_personas)
    #    was named fk_workspace_organizations_workspace_id in 001.
    #    Rename it to fk_workspace_personas_workspace_id.
    # ==================================================================
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

    # ==================================================================
    # Rename indexes for workspace_personas and personas
    #
    #    ix_workspace_organizations_workspace_id   → ix_workspace_personas_workspace_id
    #    ix_workspace_organizations_organization_id → ix_workspace_personas_persona_id
    #    ix_organizations_workspace_id              → ix_personas_workspace_id
    # ==================================================================
    op.drop_index(
        "ix_workspace_organizations_workspace_id",
        table_name="workspace_personas",
    )
    op.create_index(
        "ix_workspace_personas_workspace_id",
        "workspace_personas",
        ["workspace_id"],
    )

    op.drop_index(
        "ix_workspace_organizations_organization_id",
        table_name="workspace_personas",
    )
    op.create_index(
        "ix_workspace_personas_persona_id",
        "workspace_personas",
        ["persona_id"],
    )

    op.drop_index("ix_organizations_workspace_id", table_name="personas")
    op.create_index("ix_personas_workspace_id", "personas", ["workspace_id"])


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # ==================================================================
    # Reverse: rename indexes for workspace_personas and personas
    # ==================================================================
    op.drop_index("ix_personas_workspace_id", table_name="personas")
    op.create_index("ix_organizations_workspace_id", "personas", ["workspace_id"])

    op.drop_index("ix_workspace_personas_persona_id", table_name="workspace_personas")
    op.create_index(
        "ix_workspace_organizations_organization_id",
        "workspace_personas",
        ["persona_id"],
    )

    op.drop_index("ix_workspace_personas_workspace_id", table_name="workspace_personas")
    op.create_index(
        "ix_workspace_organizations_workspace_id",
        "workspace_personas",
        ["workspace_id"],
    )

    # ==================================================================
    # Reverse: restore workspace_organizations FK name
    # ==================================================================
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
    #    NOTE: ix_system_users_is_deleted_role_id is NOT recreated here
    #    because system_users has no is_deleted column — it was never valid.
    # ==================================================================

    # Composite / partial is_deleted indexes (002)
    op.create_index(
        "ix_organizations_workspace_id_is_deleted",
        "personas",
        ["workspace_id", "is_deleted"],
    )
    op.create_index(
        "ix_workspaces_is_deleted_subscription_plan",
        "workspaces",
        ["is_deleted", "subscription_plan"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "ix_workspaces_is_deleted_is_active",
        "workspaces",
        ["is_deleted", "is_active"],
    )

    # Simple is_deleted indexes (001)
    op.create_index("ix_homepage_info_is_deleted", "homepage_info", ["is_deleted"])
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
    # 3 (reverse). Drop is_deactivated from personas
    # ==================================================================
    op.drop_column("personas", "is_deactivated")

    # ==================================================================
    # 2 (reverse). Rename table personas → organizations
    # ==================================================================
    op.rename_table("personas", "organizations")

    # ==================================================================
    # 1 (reverse). Recreate registration_codes table
    #
    #    Recreated in full with all indexes and FK, matching 001 exactly.
    #    Uses BigInteger for id and workspace_id (no UUID).
    # ==================================================================
    op.create_table(
        "registration_codes",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("workspace_id", sa.BigInteger(), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_uses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
            name="fk_registration_codes_workspace_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_registration_codes_workspace_id",
        "registration_codes",
        ["workspace_id"],
    )
    op.create_index(
        "ix_registration_codes_is_deleted",
        "registration_codes",
        ["is_deleted"],
    )
    op.create_index(
        "ix_registration_codes_code",
        "registration_codes",
        ["code"],
    )
    # Composite index from 002
    op.create_index(
        "ix_registration_codes_workspace_id_is_deleted",
        "registration_codes",
        ["workspace_id", "is_deleted"],
    )
