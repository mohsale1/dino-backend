"""Drop display_order from tables

Revision ID: f8b9c0d1e2f3
Revises: e7a8b9c0d1e2
Create Date: 2026-04-30 00:00:00.000000

Changes:
  - tables: drop display_order column (Integer, not null, server_default=0)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "f8b9c0d1e2f3"
down_revision: Union[str, None] = "e7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Return True if *column* exists in *table* in the current DB."""
    bind = op.get_bind()
    insp = inspect(bind)
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    if _column_exists("tables", "display_order"):
        op.drop_column("tables", "display_order")


def downgrade() -> None:
    if not _column_exists("tables", "display_order"):
        op.add_column(
            "tables",
            sa.Column(
                "display_order",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
