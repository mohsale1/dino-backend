"""Add billing_config and customer_sessions tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f7
Create Date: 2026-04-30 00:00:00.000000

Changes:
  - billing_config: per-persona tax/service-charge/discount/currency configuration
  - customer_sessions: tracks a customer's active menu session (QR scan → checkout)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NOW = sa.text("now()")


# ---------------------------------------------------------------------------
# Guard helpers
# ---------------------------------------------------------------------------

def _column_exists(table: str, column: str) -> bool:
    """Return True if *column* exists in *table* in the current DB."""
    bind = op.get_bind()
    insp = inspect(bind)
    return any(c["name"] == column for c in insp.get_columns(table))


def _fk_exists(table: str, fk_name: str) -> bool:
    """Return True if a FK constraint with *fk_name* exists on *table*."""
    bind = op.get_bind()
    insp = inspect(bind)
    return any(fk["name"] == fk_name for fk in insp.get_foreign_keys(table))


def _index_exists(table: str, index_name: str) -> bool:
    """Return True if *index_name* exists on *table*."""
    bind = op.get_bind()
    insp = inspect(bind)
    return any(ix["name"] == index_name for ix in insp.get_indexes(table))


def _table_exists(table: str) -> bool:
    """Return True if *table* exists in the current DB."""
    bind = op.get_bind()
    insp = inspect(bind)
    return table in insp.get_table_names()


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. billing_config
    # ------------------------------------------------------------------
    if not _table_exists("billing_config"):
        # Drop orphaned sequences left by any previous partial run.
        # BIGSERIAL creates the sequence before the table DDL completes;
        # if the transaction rolled back the sequence may still exist.
        op.execute(sa.text("DROP SEQUENCE IF EXISTS billing_config_id_seq CASCADE"))

        op.create_table(
            "billing_config",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("workspace_id", sa.BigInteger(), nullable=False),
            sa.Column("persona_id", sa.BigInteger(), nullable=False),
            sa.Column(
                "tax_rate",
                sa.Numeric(5, 4),
                nullable=False,
                server_default=sa.text("0.0000"),
            ),
            sa.Column(
                "tax_label",
                sa.String(100),
                nullable=False,
                server_default=sa.text("'Tax'"),
            ),
            sa.Column(
                "service_charge_rate",
                sa.Numeric(5, 4),
                nullable=False,
                server_default=sa.text("0.0000"),
            ),
            sa.Column(
                "service_charge_label",
                sa.String(100),
                nullable=False,
                server_default=sa.text("'Service Charge'"),
            ),
            sa.Column(
                "discount_rate",
                sa.Numeric(5, 4),
                nullable=False,
                server_default=sa.text("0.0000"),
            ),
            sa.Column(
                "currency",
                sa.String(10),
                nullable=False,
                server_default=sa.text("'INR'"),
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
            sa.ForeignKeyConstraint(
                ["workspace_id"], ["workspaces.id"],
                name="fk_billing_config_workspace_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["persona_id"], ["personas.id"],
                name="fk_billing_config_persona_id",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("workspace_id", "persona_id", name="uq_billing_config_workspace_persona"),
            sa.CheckConstraint(
                "tax_rate >= 0 AND tax_rate <= 1",
                name="ck_billing_config_tax_rate",
            ),
            sa.CheckConstraint(
                "service_charge_rate >= 0 AND service_charge_rate <= 1",
                name="ck_billing_config_service_charge_rate",
            ),
        )

    if not _index_exists("billing_config", "ix_billing_config_workspace_id"):
        op.create_index("ix_billing_config_workspace_id", "billing_config", ["workspace_id"])

    if not _index_exists("billing_config", "ix_billing_config_persona_id"):
        op.create_index("ix_billing_config_persona_id", "billing_config", ["persona_id"])

    # ------------------------------------------------------------------
    # 2. customer_sessions
    # ------------------------------------------------------------------
    if not _table_exists("customer_sessions"):
        op.execute(sa.text("DROP SEQUENCE IF EXISTS customer_sessions_id_seq CASCADE"))

        op.create_table(
            "customer_sessions",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("workspace_id", sa.BigInteger(), nullable=False),
            sa.Column("persona_id", sa.BigInteger(), nullable=False),
            sa.Column("customer_id", sa.BigInteger(), nullable=True),
            sa.Column("order_id", sa.String(50), nullable=True),
            sa.Column("table_id", sa.BigInteger(), nullable=True),
            sa.Column("customer_name", sa.String(200), nullable=True),
            sa.Column("customer_phone", sa.String(30), nullable=True),
            sa.Column("session_token", sa.String(64), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
            sa.ForeignKeyConstraint(
                ["workspace_id"], ["workspaces.id"],
                name="fk_customer_sessions_workspace_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["persona_id"], ["personas.id"],
                name="fk_customer_sessions_persona_id",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["customer_id"], ["customers.id"],
                name="fk_customer_sessions_customer_id",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["table_id"], ["tables.id"],
                name="fk_customer_sessions_table_id",
                ondelete="SET NULL",
            ),
        )

    if not _index_exists("customer_sessions", "ix_customer_sessions_workspace_id"):
        op.create_index("ix_customer_sessions_workspace_id", "customer_sessions", ["workspace_id"])

    if not _index_exists("customer_sessions", "ix_customer_sessions_persona_id"):
        op.create_index("ix_customer_sessions_persona_id", "customer_sessions", ["persona_id"])

    if not _index_exists("customer_sessions", "ix_customer_sessions_customer_id"):
        op.create_index("ix_customer_sessions_customer_id", "customer_sessions", ["customer_id"])

    if not _index_exists("customer_sessions", "ix_customer_sessions_order_id"):
        op.create_index("ix_customer_sessions_order_id", "customer_sessions", ["order_id"])

    if not _index_exists("customer_sessions", "ix_customer_sessions_table_id"):
        op.create_index("ix_customer_sessions_table_id", "customer_sessions", ["table_id"])



# ---------------------------------------------------------------------------
# Downgrade — drops indexes then tables in reverse dependency order
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # ------------------------------------------------------------------
    # customer_sessions — indexes first, then table
    # ------------------------------------------------------------------
    if _index_exists("customer_sessions", "ix_customer_sessions_table_id"):
        op.drop_index("ix_customer_sessions_table_id", table_name="customer_sessions")

    if _index_exists("customer_sessions", "ix_customer_sessions_order_id"):
        op.drop_index("ix_customer_sessions_order_id", table_name="customer_sessions")

    if _index_exists("customer_sessions", "ix_customer_sessions_customer_id"):
        op.drop_index("ix_customer_sessions_customer_id", table_name="customer_sessions")

    if _index_exists("customer_sessions", "ix_customer_sessions_persona_id"):
        op.drop_index("ix_customer_sessions_persona_id", table_name="customer_sessions")

    if _index_exists("customer_sessions", "ix_customer_sessions_workspace_id"):
        op.drop_index("ix_customer_sessions_workspace_id", table_name="customer_sessions")

    if _table_exists("customer_sessions"):
        op.drop_table("customer_sessions")

    # ------------------------------------------------------------------
    # billing_config — indexes first, then table
    # ------------------------------------------------------------------
    if _index_exists("billing_config", "ix_billing_config_persona_id"):
        op.drop_index("ix_billing_config_persona_id", table_name="billing_config")

    if _index_exists("billing_config", "ix_billing_config_workspace_id"):
        op.drop_index("ix_billing_config_workspace_id", table_name="billing_config")

    if _table_exists("billing_config"):
        op.drop_table("billing_config")
