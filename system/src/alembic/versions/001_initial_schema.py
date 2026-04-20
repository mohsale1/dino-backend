"""Initial schema - dino-system

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-04-19 00:00:00.000000

Creates all tables for the dino-system service in correct FK dependency order:
  1. roles
  2. permissions
  3. role_permissions
  4. system_users          (deps: roles)
  5. workspaces            (deps: system_users for referred_by resolved at app level)
  6. workspace_organizations (deps: workspaces)
  7. organizations         (no enforced FK — workspace_id stored as plain BigInteger)
  8. registration_codes    (deps: workspaces)
  9. homepage_info
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
        sa.Column(
            "role_type",
            sa.SmallInteger(),
            nullable=False,
            server_default="0",
            comment="0=System, 1=Application",
        ),
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
        sa.Column(
            "category",
            sa.String(50),
            nullable=False,
            comment="system or application",
        ),
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
    # 4. system_users
    #
    #    id is VARCHAR(4) — the 4-digit numeric referral code assigned by
    #    application logic (e.g. "1000", "1042").  It is NOT auto-incremented
    #    and has no server_default; the application always supplies the value.
    #    There is no separate human_id column — id IS the referral code.
    #    role_id is BigInteger (references roles.id which is now BigInteger).
    # ------------------------------------------------------------------
    op.create_table(
        "system_users",
        sa.Column(
            "id",
            sa.String(4),
            primary_key=True,
            nullable=False,
            comment="4-digit numeric referral code assigned by the application (e.g. '1000')",
        ),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        # role_id is nullable — a system user may exist before a role is assigned
        sa.Column("role_id", sa.BigInteger(), nullable=True),
        sa.Column("last_login", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true",
                  comment="False = deactivated or deleted"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW_DEFAULT,
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name="fk_system_users_role_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_system_users_email", "system_users", ["email"])
    op.create_index("ix_system_users_role_id", "system_users", ["role_id"])

    # ------------------------------------------------------------------
    # 5. workspaces
    #    owner_id is String(4) — references system_users.id (4-digit code).
    #    referred_by stores the system_user id (4-digit string) —
    #    kept as String(10) for forward-compatibility; no enforced FK
    #    because it is a soft cross-service reference.
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
            comment="4-digit system_users.id of the owning system user",
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
        sa.Column("subscription_start_date", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("next_billing_date", sa.TIMESTAMP(timezone=True), nullable=True),
        # MRR — monthly recurring revenue; defaults to 0, never NULL
        sa.Column(
            "mrr",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
            comment="Monthly recurring revenue in account currency",
        ),
        # Referral — system_user id (4-digit string); String(10) for safety
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
    op.create_index("ix_workspaces_referred_by", "workspaces", ["referred_by"])

    # ------------------------------------------------------------------
    # 6. workspace_organizations  (junction: workspaces <-> organizations)
    #    Composite PK on (workspace_id, organization_id) — no separate id column.
    #    organization_id is stored without an enforced FK because
    #    organizations may be managed by the dino-application service.
    # ------------------------------------------------------------------
    op.create_table(
        "workspace_organizations",
        sa.Column("workspace_id", sa.BigInteger(), nullable=False, primary_key=True),
        sa.Column(
            "organization_id",
            sa.BigInteger(),
            nullable=False,
            primary_key=True,
            comment="Cross-service reference to organizations table",
        ),
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
    # 7. organizations
    #    workspace_id stored without enforced FK (cross-service reference).
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
        sa.Column(
            "workspace_id",
            sa.BigInteger(),
            nullable=False,
            comment="Cross-service reference to workspaces table",
        ),
        sa.Column(
            "organization_type",
            sa.SmallInteger(),
            nullable=False,
            server_default="0",
            comment="0=FOOD, 1=NON_FOOD",
        ),
        sa.Column(
            "order_type",
            sa.SmallInteger(),
            nullable=False,
            server_default="0",
            comment="0=Online, 1=Manual/Counter",
        ),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default="true"),
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
    )
    op.create_index("ix_organizations_workspace_id", "organizations", ["workspace_id"])
    op.create_index("ix_organizations_is_deleted", "organizations", ["is_deleted"])

    # ------------------------------------------------------------------
    # 8. registration_codes
    #
    #    workspace_id is nullable with SET NULL so that deleting a workspace
    #    orphans the code rather than cascading the delete — matches the ORM.
    # ------------------------------------------------------------------
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
        # nullable — SET NULL when the parent workspace is deleted
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
        "ix_registration_codes_workspace_id", "registration_codes", ["workspace_id"]
    )
    op.create_index(
        "ix_registration_codes_is_deleted", "registration_codes", ["is_deleted"]
    )
    op.create_index(
        "ix_registration_codes_code", "registration_codes", ["code"]
    )

    # ------------------------------------------------------------------
    # 9. homepage_info
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
    # Drop in reverse dependency order.
    # Indexes on each table are dropped automatically when the table is dropped;
    # they are listed here for clarity and symmetry with upgrade().
    op.drop_index("ix_homepage_info_is_deleted", table_name="homepage_info")
    op.drop_table("homepage_info")

    op.drop_index("ix_registration_codes_code", table_name="registration_codes")
    op.drop_index("ix_registration_codes_is_deleted", table_name="registration_codes")
    op.drop_index("ix_registration_codes_workspace_id", table_name="registration_codes")
    op.drop_table("registration_codes")

    op.drop_index("ix_organizations_is_deleted", table_name="organizations")
    op.drop_index("ix_organizations_workspace_id", table_name="organizations")
    op.drop_table("organizations")

    op.drop_index(
        "ix_workspace_organizations_organization_id",
        table_name="workspace_organizations",
    )
    op.drop_index(
        "ix_workspace_organizations_workspace_id",
        table_name="workspace_organizations",
    )
    op.drop_table("workspace_organizations")

    op.drop_index("ix_workspaces_referred_by", table_name="workspaces")
    op.drop_index("ix_workspaces_owner_id", table_name="workspaces")
    op.drop_index("ix_workspaces_is_deleted", table_name="workspaces")
    op.drop_table("workspaces")

    op.drop_index("ix_system_users_role_id", table_name="system_users")
    op.drop_index("ix_system_users_email", table_name="system_users")
    op.drop_table("system_users")

    op.drop_index(
        "ix_role_permissions_permission_id", table_name="role_permissions"
    )
    op.drop_index("ix_role_permissions_role_id", table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index("ix_permissions_name_trgm", table_name="permissions")
    op.drop_index("ix_permissions_is_deleted", table_name="permissions")
    op.drop_table("permissions")

    op.drop_index("ix_roles_role_type", table_name="roles")
    op.drop_index("ix_roles_is_deleted", table_name="roles")
    op.drop_table("roles")
