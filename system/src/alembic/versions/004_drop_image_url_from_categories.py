"""Drop image_url from categories

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-04-30 00:00:00.000000

Changes:
  - categories: drop image_url column (String 500, nullable)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Return True if *column* exists in *table* in the current DB."""
    bind = op.get_bind()
    insp = inspect(bind)
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    if _column_exists("categories", "image_url"):
        op.drop_column("categories", "image_url")


def downgrade() -> None:
    if not _column_exists("categories", "image_url"):
        op.add_column(
            "categories",
            sa.Column("image_url", sa.String(500), nullable=True),
        )
