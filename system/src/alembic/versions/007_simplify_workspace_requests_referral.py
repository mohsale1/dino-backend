"""Simplify workspace_requests referral columns: drop referred_by, rename referred_by_user_id â†’ referred_by

Revision ID: a1b2c3d4e5f7
Revises: f8b9c0d1e2f3
Create Date: 2026-04-30 00:00:00.000000

Changes:
  - workspace_requests: drop index ix_workspace_requests_referred_by
  - workspace_requests: drop FK fk_workspace_requests_referred_by
  - workspace_requests: drop column referred_by
      (was the user.id resolved from the referral email â€” redundant, email already captures this)
  - workspace_requests: drop index ix_workspace_requests_referred_by_id
  - workspace_requests: drop FK fk_workspace_requests_referred_by_id
  - workspace_requests: rename column referred_by_user_id â†’ referred_by
      (the logged-in system user who submitted the request â€” the meaningful FK)
  - workspace_requests: recreate FK fk_workspace_requests_referred_by on referred_by â†’ users.id SET NULL
  - workspace_requests: recreate index ix_workspace_requests_referred_by
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "f8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. workspace_requests â€” drop index ix_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if _index_exists("workspace_requests", "ix_workspace_requests_referred_by"):
        op.drop_index("ix_workspace_requests_referred_by", table_name="workspace_requests")

    # -----------------------------------------------------------------------
    # 2. workspace_requests â€” drop FK fk_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if _fk_exists("workspace_requests", "fk_workspace_requests_referred_by"):
        op.drop_constraint(
            "fk_workspace_requests_referred_by",
            "workspace_requests",
            type_="foreignkey",
        )

    # -----------------------------------------------------------------------
    # 3. workspace_requests â€” drop column referred_by
    # -----------------------------------------------------------------------
    if _column_exists("workspace_requests", "referred_by"):
        op.drop_column("workspace_requests", "referred_by")

    # -----------------------------------------------------------------------
    # 4. workspace_requests â€” drop index ix_workspace_requests_referred_by_id
    # -----------------------------------------------------------------------
    if _index_exists("workspace_requests", "ix_workspace_requests_referred_by_id"):
        op.drop_index(
            "ix_workspace_requests_referred_by_id",
            table_name="workspace_requests",
        )

    # -----------------------------------------------------------------------
    # 5. workspace_requests â€” drop FK fk_workspace_requests_referred_by_id
    # -----------------------------------------------------------------------
    if _fk_exists("workspace_requests", "fk_workspace_requests_referred_by_id"):
        op.drop_constraint(
            "fk_workspace_requests_referred_by_id",
            "workspace_requests",
            type_="foreignkey",
        )

    # -----------------------------------------------------------------------
    # 6. workspace_requests â€” rename column referred_by_user_id â†’ referred_by
    # -----------------------------------------------------------------------
    if _column_exists("workspace_requests", "referred_by_user_id") and not _column_exists(
        "workspace_requests", "referred_by"
    ):
        op.alter_column(
            "workspace_requests",
            "referred_by_user_id",
            new_column_name="referred_by",
        )

    # -----------------------------------------------------------------------
    # 7. workspace_requests â€” recreate FK fk_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if not _fk_exists("workspace_requests", "fk_workspace_requests_referred_by"):
        op.create_foreign_key(
            "fk_workspace_requests_referred_by",
            "workspace_requests",
            "users",
            ["referred_by"],
            ["id"],
            ondelete="SET NULL",
        )

    # -----------------------------------------------------------------------
    # 8. workspace_requests â€” recreate index ix_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if not _index_exists("workspace_requests", "ix_workspace_requests_referred_by"):
        op.create_index(
            "ix_workspace_requests_referred_by",
            "workspace_requests",
            ["referred_by"],
        )


# ---------------------------------------------------------------------------
# Downgrade â€” fully reverses all upgrade steps in reverse order
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. workspace_requests â€” drop index ix_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if _index_exists("workspace_requests", "ix_workspace_requests_referred_by"):
        op.drop_index(
            "ix_workspace_requests_referred_by",
            table_name="workspace_requests",
        )

    # -----------------------------------------------------------------------
    # 2. workspace_requests â€” drop FK fk_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if _fk_exists("workspace_requests", "fk_workspace_requests_referred_by"):
        op.drop_constraint(
            "fk_workspace_requests_referred_by",
            "workspace_requests",
            type_="foreignkey",
        )

    # -----------------------------------------------------------------------
    # 3. workspace_requests â€” rename column referred_by â†’ referred_by_user_id
    # -----------------------------------------------------------------------
    if _column_exists("workspace_requests", "referred_by") and not _column_exists(
        "workspace_requests", "referred_by_user_id"
    ):
        op.alter_column(
            "workspace_requests",
            "referred_by",
            new_column_name="referred_by_user_id",
        )

    # -----------------------------------------------------------------------
    # 4. workspace_requests â€” restore FK fk_workspace_requests_referred_by_id
    # -----------------------------------------------------------------------
    if not _fk_exists("workspace_requests", "fk_workspace_requests_referred_by_id"):
        op.create_foreign_key(
            "fk_workspace_requests_referred_by_id",
            "workspace_requests",
            "users",
            ["referred_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # -----------------------------------------------------------------------
    # 5. workspace_requests â€” restore index ix_workspace_requests_referred_by_id
    # -----------------------------------------------------------------------
    if not _index_exists("workspace_requests", "ix_workspace_requests_referred_by_id"):
        op.create_index(
            "ix_workspace_requests_referred_by_id",
            "workspace_requests",
            ["referred_by_user_id"],
        )

    # -----------------------------------------------------------------------
    # 6. workspace_requests â€” restore column referred_by
    # -----------------------------------------------------------------------
    if not _column_exists("workspace_requests", "referred_by"):
        op.add_column(
            "workspace_requests",
            sa.Column(
                "referred_by",
                sa.BigInteger(),
                nullable=True,
                comment="User ID resolved from the referral email (person being referred)",
            ),
        )

    # -----------------------------------------------------------------------
    # 7. workspace_requests â€” restore FK fk_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if not _fk_exists("workspace_requests", "fk_workspace_requests_referred_by"):
        op.create_foreign_key(
            "fk_workspace_requests_referred_by",
            "workspace_requests",
            "users",
            ["referred_by"],
            ["id"],
            ondelete="SET NULL",
        )

    # -----------------------------------------------------------------------
    # 8. workspace_requests â€” restore index ix_workspace_requests_referred_by
    # -----------------------------------------------------------------------
    if not _index_exists("workspace_requests", "ix_workspace_requests_referred_by"):
        op.create_index(
            "ix_workspace_requests_referred_by",
            "workspace_requests",
            ["referred_by"],
        )
