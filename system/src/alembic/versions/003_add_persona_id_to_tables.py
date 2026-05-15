"""Add persona_id to tables

Revision ID: d5e6f7a8b9c0
Revises: c3d4e5f6a7b8
Create Date: 2026-04-30 00:00:00.000000

Changes:
  - tables: add persona_id (BigInteger, FK → personas.id SET NULL, nullable)
  - tables: back-fill persona_id from parent area for all existing rows
  - tables: create index ix_tables_persona_id
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    # 1. Add persona_id column (nullable so existing rows are not rejected)
    # ------------------------------------------------------------------
    if not _column_exists("tables", "persona_id"):
        op.add_column(
            "tables",
            sa.Column(
                "persona_id",
                sa.BigInteger(),
                nullable=True,
                comment="Denormalised from areas.persona_id for direct query scoping",
            ),
        )

    # ------------------------------------------------------------------
    # 2. FK constraint: tables.persona_id → personas.id
    # ------------------------------------------------------------------
    if not _fk_exists("tables", "fk_tables_persona_id"):
        op.create_foreign_key(
            "fk_tables_persona_id", "tables", "personas",
            ["persona_id"], ["id"], ondelete="SET NULL",
        )

    # ------------------------------------------------------------------
    # 3. Back-fill persona_id from the parent area for all existing rows
    # ------------------------------------------------------------------
    op.execute(
        sa.text(
            """
            UPDATE tables t
            SET    persona_id = a.persona_id
            FROM   areas a
            WHERE  t.area_id = a.id
              AND  t.persona_id IS NULL
            """
        )
    )

    # ------------------------------------------------------------------
    # 4. Index on persona_id
    # ------------------------------------------------------------------
    if not _index_exists("tables", "ix_tables_persona_id"):
        op.create_index("ix_tables_persona_id", "tables", ["persona_id"])


def downgrade() -> None:
    op.drop_index("ix_tables_persona_id", table_name="tables")
    op.drop_constraint("fk_tables_persona_id", "tables", type_="foreignkey")
    op.drop_column("tables", "persona_id")
