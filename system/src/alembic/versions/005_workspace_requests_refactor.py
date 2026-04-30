"""Refactor workspace_requests: rename user_idâ†’referred_by, add referred_by_user_id; drop workspaces.requested_by

Revision ID: e7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-04-30 00:00:00.000000

Changes:
  - workspaces: drop index ix_workspaces_requested_by, FK fk_workspaces_requested_by, column requested_by
  - workspace_requests: rename column user_id â†’ referred_by
      - rename FK  fk_workspace_requests_user_id  â†’ fk_workspace_requests_referred_by
      - rename index ix_workspace_requests_user_id â†’ ix_workspace_requests_referred_by
  - workspace_requests: add column referred_by_user_id (BigInteger, nullable, FK â†’ users.id SET NULL)
      - FK  fk_workspace_requests_referred_by_user_id
      - index ix_workspace_requests_referred_by_user_id
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "e7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
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
    # 1. workspaces â€” drop ix_workspaces_requested_by index
    # -----------------------------------------------------------------------
    if _index_exists("workspaces", "ix_workspaces_requested_by"):
        op.drop_index("ix_workspaces_requested_by", table_name="workspaces")

    # -----------------------------------------------------------------------
    # 2. workspaces â€” drop fk_workspaces_requested_by FK
    # -----------------------------------------------------------------------
    if _fk_exists("workspaces", "fk_workspaces_requested_by"):
        op.drop_constraint("fk_workspaces_requested_by", "workspaces", type_="foreignkey")

    # -----------------------------------------------------------------------
    # 3. workspaces â€” drop requested_by column
    # -----------------------------------------------------------------------
    if _column_exists("workspaces", "requested_by"):
        op.drop_column("workspaces", "requested_by")

    # -----------------------------------------------------------------------
    # 4. workspace_requests â€” drop old index on user_id before renaming column
    # -----------------------------------------------------------------------
    if _index_exists("workspace_requests", "ix_workspace_requests_user_id"):
        op.drop_index("ix_workspace_requests_user_id", table_name="workspace_requests")

    # -----------------------------------------------------------------------
    # 5. workspace_requests â€” drop old FK on user_id before renaming column
    # -----------------------------------------------------------------------
    if _fk_exists("workspace_requests", "fk_workspace_requests_user_id"):
        op.drop_constraint("fk_workspace_requests_user_id", "workspace_requests", type_="foreignkey")

    # -----------------------------------------------------------------------
    # 6. workspace_requests â€” rename column user_id â†’ referred_by
    # -----------------------------------------------------------------------
    if _column_exists("workspace_requests", "user_id") and not _column_exists("workspace_requests", "referred_by"):
        op.alter_column("workspace_requests", "user_id", new_column_name="referred_by")

    # -----------------------------------------------------------------------
    # 7. workspace_requests â€” recreate FK on referred_by â†’ users.id SET NULL
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
    # 8. workspace_requests â€” recreate index on referred_by
    # -----------------------------------------------------------------------
    if not _index_exists("workspace_requests", "ix_workspace_requests_referred_by"):
        op.create_index(
            "ix_workspace_requests_referred_by",
            "workspace_requests",
            ["referred_by"],
        )

    # -----------------------------------------------------------------------
    # 9. workspace_requests â€” add referred_by_user_id column
    # -----------------------------------------------------------------------
    if not _column_exists("workspace_requests", "referred_by_user_id"):
        op.add_column(
            "workspace_requests",
            sa.Column(
                "referred_by_user_id",
                sa.BigInteger(),
                nullable=True,
                comment="System user who submitted the referral request",
            ),
        )

    # -----------------------------------------------------------------------
    # 10. workspace_requests â€” FK for referred_by_user_id â†’ users.id SET NULL
    # -----------------------------------------------------------------------
    if not _fk_exists("workspace_requests", "fk_workspace_requests_referred_by_user_id"):
        op.create_foreign_key(
            "fk_workspace_requests_referred_by_user_id",
            "workspace_requests",
            "users",
            ["referred_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # -----------------------------------------------------------------------
    # 11. workspace_requests â€” index on referred_by_user_id
    # -----------------------------------------------------------------------
    if not _index_exists("workspace_requests", "ix_workspace_requests_referred_by_user_id"):
        op.create_index(
            "ix_workspace_requests_referred_by_user_id",
            "workspace_requests",
            ["referred_by_user_id"],
        )


# ---------------------------------------------------------------------------
# Downgrade â€” fully reverses all upgrade steps in reverse order
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. workspace_requests â€” drop index + FK + column referred_by_user_id
    # -----------------------------------------------------------------------
    if _index_exists("workspace_requests", "ix_workspace_requests_referred_by_user_id"):
        op.drop_index("ix_workspace_requests_referred_by_user_id", table_name="workspace_requests")

    if _fk_exists("workspace_requests", "fk_workspace_requests_referred_by_user_id"):
        op.drop_constraint(
            "fk_workspace_requests_referred_by_user_id",
            "workspace_requests",
            type_="foreignkey",
        )

    if _column_exists("workspace_requests", "referred_by_user_id"):
        op.drop_column("workspace_requests", "referred_by_user_id")

    # -----------------------------------------------------------------------
    # 2. workspace_requests â€” drop index + FK on referred_by before renaming back
    # -----------------------------------------------------------------------
    if _index_exists("workspace_requests", "ix_workspace_requests_referred_by"):
        op.drop_index("ix_workspace_requests_referred_by", table_name="workspace_requests")

    if _fk_exists("workspace_requests", "fk_workspace_requests_referred_by"):
        op.drop_constraint(
            "fk_workspace_requests_referred_by",
            "workspace_requests",
            type_="foreignkey",
        )

    # -----------------------------------------------------------------------
    # 3. workspace_requests â€” rename column referred_by â†’ user_id
    # -----------------------------------------------------------------------
    if _column_exists("workspace_requests", "referred_by") and not _column_exists("workspace_requests", "user_id"):
        op.alter_column("workspace_requests", "referred_by", new_column_name="user_id")

    # -----------------------------------------------------------------------
    # 4. workspace_requests â€” restore FK fk_workspace_requests_user_id
    # -----------------------------------------------------------------------
    if not _fk_exists("workspace_requests", "fk_workspace_requests_user_id"):
        op.create_foreign_key(
            "fk_workspace_requests_user_id",
            "workspace_requests",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # -----------------------------------------------------------------------
    # 5. workspace_requests â€” restore index ix_workspace_requests_user_id
    # -----------------------------------------------------------------------
    if not _index_exists("workspace_requests", "ix_workspace_requests_user_id"):
        op.create_index(
            "ix_workspace_requests_user_id",
            "workspace_requests",
            ["user_id"],
        )

    # -----------------------------------------------------------------------
    # 6. workspaces â€” restore requested_by column
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # 7. workspaces â€” restore FK fk_workspaces_requested_by
    # -----------------------------------------------------------------------
    if not _fk_exists("workspaces", "fk_workspaces_requested_by"):
        op.create_foreign_key(
            "fk_workspaces_requested_by",
            "workspaces",
            "users",
            ["requested_by"],
            ["id"],
            ondelete="SET NULL",
        )

    # -----------------------------------------------------------------------
    # 8. workspaces â€” restore index ix_workspaces_requested_by
    # -----------------------------------------------------------------------
    if not _index_exists("workspaces", "ix_workspaces_requested_by"):
        op.create_index(
            "ix_workspaces_requested_by",
            "workspaces",
            ["requested_by"],
        )
