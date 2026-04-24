"""Add workspace_requests table and update workspaces

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-23 00:00:00.000000

Changes:
  - workspaces: drop referred_by FK and column (was created in 001)
  - workspaces: add requested_by (BigInteger, FK -> users.id SET NULL)
  - workspaces: add is_verified (Boolean, NOT NULL, server_default false)
  - Create workspace_requests table
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NOW = sa.text("now()")


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


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. workspaces â€” drop referred_by FK (created in 001_initial_schema)
    # ------------------------------------------------------------------
    if _fk_exists("workspaces", "fk_workspaces_referred_by"):
        op.drop_constraint("fk_workspaces_referred_by", "workspaces", type_="foreignkey")

    # ------------------------------------------------------------------
    # 2. workspaces â€” drop referred_by column
    # ------------------------------------------------------------------
    if _column_exists("workspaces", "referred_by"):
        op.drop_column("workspaces", "referred_by")

    # ------------------------------------------------------------------
    # 3. workspaces â€” add requested_by column
    # ------------------------------------------------------------------
    if not _column_exists("workspaces", "requested_by"):
        op.add_column(
            "workspaces",
            sa.Column(
                "requested_by",
                sa.BigInteger(),
                nullable=True,
                comment="System user who submitted the workspace verification request",
            ),
        )

    # ------------------------------------------------------------------
    # 4. workspaces â€” FK for requested_by -> users.id
    # ------------------------------------------------------------------
    if not _fk_exists("workspaces", "fk_workspaces_requested_by"):
        op.create_foreign_key(
            "fk_workspaces_requested_by", "workspaces", "users",
            ["requested_by"], ["id"], ondelete="SET NULL",
        )

    # ------------------------------------------------------------------
    # 5. workspaces â€” index on requested_by
    # ------------------------------------------------------------------
    if not _index_exists("workspaces", "ix_workspaces_requested_by"):
        op.create_index("ix_workspaces_requested_by", "workspaces", ["requested_by"])

    # ------------------------------------------------------------------
    # 6. workspaces â€” add is_verified column
    # ------------------------------------------------------------------
    if not _column_exists("workspaces", "is_verified"):
        op.add_column(
            "workspaces",
            sa.Column(
                "is_verified",
                sa.Boolean(),
                nullable=False,
                server_default="false",
                comment="Set to true when an admin approves the workspace request",
            ),
        )

    # ------------------------------------------------------------------
    # 7. Create workspace_requests table
    # ------------------------------------------------------------------
    op.create_table(
        "workspace_requests",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Sequence("workspace_requests_id_seq"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
            comment="pending / approved / rejected",
        ),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_workspace_requests_user_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"],
            name="fk_workspace_requests_workspace_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"], ["users.id"],
            name="fk_workspace_requests_reviewed_by",
            ondelete="SET NULL",
        ),
    )

    # ------------------------------------------------------------------
    # 8. workspace_requests â€” indexes
    # ------------------------------------------------------------------
    op.create_index("ix_workspace_requests_user_id", "workspace_requests", ["user_id"])
    op.create_index("ix_workspace_requests_workspace_id", "workspace_requests", ["workspace_id"])
    op.create_index("ix_workspace_requests_status", "workspace_requests", ["status"])
    op.create_index("ix_workspace_requests_is_active", "workspace_requests", ["is_active"])


def downgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Drop workspace_requests indexes then table
    # ------------------------------------------------------------------
    op.drop_index("ix_workspace_requests_is_active", table_name="workspace_requests")
    op.drop_index("ix_workspace_requests_status", table_name="workspace_requests")
    op.drop_index("ix_workspace_requests_workspace_id", table_name="workspace_requests")
    op.drop_index("ix_workspace_requests_user_id", table_name="workspace_requests")
    op.drop_table("workspace_requests")

    # ------------------------------------------------------------------
    # 2. workspaces â€” drop is_verified column
    # ------------------------------------------------------------------
    op.drop_column("workspaces", "is_verified")

    # ------------------------------------------------------------------
    # 3. workspaces â€” drop requested_by index, FK, and column
    # ------------------------------------------------------------------
    op.drop_index("ix_workspaces_requested_by", table_name="workspaces")
    op.drop_constraint("fk_workspaces_requested_by", "workspaces", type_="foreignkey")
    op.drop_column("workspaces", "requested_by")

    # ------------------------------------------------------------------
    # 4. workspaces â€” restore referred_by column and FK (as in 001)
    # ------------------------------------------------------------------
    op.add_column(
        "workspaces",
        sa.Column("referred_by", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_workspaces_referred_by", "workspaces", "users",
        ["referred_by"], ["id"], ondelete="SET NULL",
    )