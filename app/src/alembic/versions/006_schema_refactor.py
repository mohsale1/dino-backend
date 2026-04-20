"""Schema refactor — workspaces, personas, users, customers

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-04-20 00:00:00.000000

Summary of changes
==================
1.  workspaces table
      - Drop columns: slug, logo_url, website, timezone, currency,
        plan, plan_status, billing_cycle, billing_email, billing_name,
        billing_address, billing_city, billing_state, billing_country,
        billing_postal_code, billing_phone, tax_id, subscription_id,
        subscription_start, subscription_end, trial_end,
        max_personas, max_users
      - Drop index: ix_workspaces_plan (if exists)

2.  Create table workspace_billing (one-to-one with workspaces)
      - id                  BIGINT PK autoincrement
      - workspace_id        BIGINT NOT NULL UNIQUE FK→workspaces.id CASCADE
      - plan                VARCHAR(50)  NOT NULL DEFAULT 'free'
      - plan_status         VARCHAR(50)  NOT NULL DEFAULT 'active'
      - billing_cycle       VARCHAR(20)  nullable
      - billing_email       VARCHAR(254) nullable
      - billing_name        VARCHAR(200) nullable
      - billing_address     TEXT         nullable
      - billing_city        VARCHAR(100) nullable
      - billing_state       VARCHAR(100) nullable
      - billing_country     VARCHAR(100) nullable
      - billing_postal_code VARCHAR(20)  nullable
      - billing_phone       VARCHAR(30)  nullable
      - tax_id              VARCHAR(100) nullable
      - subscription_id     VARCHAR(200) nullable
      - subscription_start  TIMESTAMPTZ  nullable
      - subscription_end    TIMESTAMPTZ  nullable
      - trial_end           TIMESTAMPTZ  nullable
      - max_personas        INTEGER NOT NULL DEFAULT 1
      - max_users           INTEGER NOT NULL DEFAULT 5
      - updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()

3.  personas table
      - Rename column organization_type → persona_type
      - Rename index ix_personas_organization_type → ix_personas_persona_type

4.  Create table user_personas (many-to-many: application_users ↔ personas)
      - user_id    BIGINT NOT NULL FK→application_users.id CASCADE PK
      - persona_id BIGINT NOT NULL FK→personas.id CASCADE PK

5.  application_users table
      - Drop column persona_id
      - Drop index ix_application_users_persona_id (if exists)

6.  customers table
      - Add column persona_id BIGINT nullable FK→personas.id SET NULL
      - Create index ix_customers_persona_id

downgrade() reverses all steps in reverse order.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------
def upgrade() -> None:

    # ==================================================================
    # 1. workspaces — drop billing/plan/meta columns
    # ==================================================================
    columns_to_drop = [
        "slug",
        "logo_url",
        "website",
        "timezone",
        "currency",
        "plan",
        "plan_status",
        "billing_cycle",
        "billing_email",
        "billing_name",
        "billing_address",
        "billing_city",
        "billing_state",
        "billing_country",
        "billing_postal_code",
        "billing_phone",
        "tax_id",
        "subscription_id",
        "subscription_start",
        "subscription_end",
        "trial_end",
        "max_personas",
        "max_users",
    ]

    # Drop the plan index first (index on a column we are about to drop)
    op.execute("DROP INDEX IF EXISTS ix_workspaces_plan")
    op.execute("DROP INDEX IF EXISTS ix_workspaces_slug")

    for col in columns_to_drop:
        op.drop_column("workspaces", col)

    # ==================================================================
    # 2. Create workspace_billing table
    # ==================================================================
    op.create_table(
        "workspace_billing",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "workspace_id",
            sa.BigInteger(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE", name="fk_workspace_billing_workspace_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("plan_status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("billing_cycle", sa.String(20), nullable=True),
        sa.Column("billing_email", sa.String(254), nullable=True),
        sa.Column("billing_name", sa.String(200), nullable=True),
        sa.Column("billing_address", sa.Text(), nullable=True),
        sa.Column("billing_city", sa.String(100), nullable=True),
        sa.Column("billing_state", sa.String(100), nullable=True),
        sa.Column("billing_country", sa.String(100), nullable=True),
        sa.Column("billing_postal_code", sa.String(20), nullable=True),
        sa.Column("billing_phone", sa.String(30), nullable=True),
        sa.Column("tax_id", sa.String(100), nullable=True),
        sa.Column("subscription_id", sa.String(200), nullable=True),
        sa.Column("subscription_start", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("subscription_end", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("trial_end", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("max_personas", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_users", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("workspace_id", name="uq_workspace_billing_workspace_id"),
    )
    op.create_index("ix_workspace_billing_workspace_id", "workspace_billing", ["workspace_id"])

    # ==================================================================
    # 3. personas — rename organization_type → persona_type
    # ==================================================================
    op.alter_column("personas", "organization_type", new_column_name="persona_type")
    op.execute("DROP INDEX IF EXISTS ix_personas_organization_type")
    op.create_index("ix_personas_persona_type", "personas", ["persona_type"])

    # ==================================================================
    # 4. Create user_personas association table
    # ==================================================================
    op.create_table(
        "user_personas",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("application_users.id", ondelete="CASCADE", name="fk_user_personas_user_id"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "persona_id",
            sa.BigInteger(),
            sa.ForeignKey("personas.id", ondelete="CASCADE", name="fk_user_personas_persona_id"),
            primary_key=True,
            nullable=False,
        ),
    )
    op.create_index("ix_user_personas_user_id", "user_personas", ["user_id"])
    op.create_index("ix_user_personas_persona_id", "user_personas", ["persona_id"])

    # ==================================================================
    # 5. application_users — drop persona_id column
    # ==================================================================
    op.execute("DROP INDEX IF EXISTS ix_application_users_persona_id")
    # Drop FK constraint before dropping the column
    op.drop_constraint("fk_application_users_persona_id", "application_users", type_="foreignkey")
    op.drop_column("application_users", "persona_id")

    # ==================================================================
    # 6. customers — add persona_id column
    # ==================================================================
    op.add_column(
        "customers",
        sa.Column("persona_id", sa.BigInteger(), nullable=True),
    )
    op.create_index("ix_customers_persona_id", "customers", ["persona_id"])
    op.create_foreign_key(
        "fk_customers_persona_id",
        "customers",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------
def downgrade() -> None:

    # ==================================================================
    # 6 (reverse). customers — drop persona_id
    # ==================================================================
    op.drop_constraint("fk_customers_persona_id", "customers", type_="foreignkey")
    op.drop_index("ix_customers_persona_id", table_name="customers")
    op.drop_column("customers", "persona_id")

    # ==================================================================
    # 5 (reverse). application_users — restore persona_id
    # ==================================================================
    op.add_column(
        "application_users",
        sa.Column("persona_id", sa.BigInteger(), nullable=True),
    )
    op.create_index("ix_application_users_persona_id", "application_users", ["persona_id"])
    op.create_foreign_key(
        "fk_application_users_persona_id",
        "application_users",
        "personas",
        ["persona_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ==================================================================
    # 4 (reverse). Drop user_personas table
    # ==================================================================
    op.drop_index("ix_user_personas_persona_id", table_name="user_personas")
    op.drop_index("ix_user_personas_user_id", table_name="user_personas")
    op.drop_table("user_personas")

    # ==================================================================
    # 3 (reverse). personas — rename persona_type → organization_type
    # ==================================================================
    op.execute("DROP INDEX IF EXISTS ix_personas_persona_type")
    op.alter_column("personas", "persona_type", new_column_name="organization_type")
    op.create_index("ix_personas_organization_type", "personas", ["organization_type"])

    # ==================================================================
    # 2 (reverse). Drop workspace_billing table
    # ==================================================================
    op.drop_index("ix_workspace_billing_workspace_id", table_name="workspace_billing")
    op.drop_table("workspace_billing")

    # ==================================================================
    # 1 (reverse). workspaces — restore dropped columns
    # ==================================================================
    op.add_column("workspaces", sa.Column("slug", sa.String(100), nullable=True))
    op.add_column("workspaces", sa.Column("logo_url", sa.String(500), nullable=True))
    op.add_column("workspaces", sa.Column("website", sa.String(300), nullable=True))
    op.add_column("workspaces", sa.Column("timezone", sa.String(100), nullable=False, server_default="UTC"))
    op.add_column("workspaces", sa.Column("currency", sa.String(10), nullable=False, server_default="USD"))
    op.add_column("workspaces", sa.Column("plan", sa.String(50), nullable=False, server_default="free"))
    op.add_column("workspaces", sa.Column("plan_status", sa.String(50), nullable=False, server_default="active"))
    op.add_column("workspaces", sa.Column("billing_cycle", sa.String(20), nullable=True))
    op.add_column("workspaces", sa.Column("billing_email", sa.String(254), nullable=True))
    op.add_column("workspaces", sa.Column("billing_name", sa.String(200), nullable=True))
    op.add_column("workspaces", sa.Column("billing_address", sa.Text(), nullable=True))
    op.add_column("workspaces", sa.Column("billing_city", sa.String(100), nullable=True))
    op.add_column("workspaces", sa.Column("billing_state", sa.String(100), nullable=True))
    op.add_column("workspaces", sa.Column("billing_country", sa.String(100), nullable=True))
    op.add_column("workspaces", sa.Column("billing_postal_code", sa.String(20), nullable=True))
    op.add_column("workspaces", sa.Column("billing_phone", sa.String(30), nullable=True))
    op.add_column("workspaces", sa.Column("tax_id", sa.String(100), nullable=True))
    op.add_column("workspaces", sa.Column("subscription_id", sa.String(200), nullable=True))
    op.add_column("workspaces", sa.Column("subscription_start", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("workspaces", sa.Column("subscription_end", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("workspaces", sa.Column("trial_end", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("workspaces", sa.Column("max_personas", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("workspaces", sa.Column("max_users", sa.Integer(), nullable=False, server_default="5"))
    op.create_index("ix_workspaces_plan", "workspaces", ["plan"])
