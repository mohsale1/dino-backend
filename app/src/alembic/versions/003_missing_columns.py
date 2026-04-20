"""Add missing columns found during ORM vs migration cross-validation

Revision ID: d4e5f6a7b8c9
Revises: b2c3d4e5f6a7
Create Date: 2026-04-19 00:00:00.000000

Cross-validation findings (ORM models vs 001_initial_schema.py):
=================================================================

TABLE: orders
  MISSING from migration (present in ORM):
    - order_type          VARCHAR(30)   NOT NULL  DEFAULT 'dine_in'
    - payment_method      VARCHAR(50)   NULL
    - subtotal            NUMERIC(12,2) NOT NULL  DEFAULT 0
    - tax_amount          NUMERIC(12,2) NOT NULL  DEFAULT 0
    - service_charge      NUMERIC(12,2) NOT NULL  DEFAULT 0
    - discount_amount     NUMERIC(12,2) NOT NULL  DEFAULT 0
    - special_instructions TEXT         NULL
  NOTE: migration has shipping_address (JSONB) and notes (Text) which are
        absent from the ORM — those are left in place (migration-only columns
        are not removed here; a separate cleanup migration can handle that).

TABLE: order_items
  COLUMN NAME MISMATCH:
    - migration has product_id (String) / product_name (String)
    - ORM has    item_id (BigInteger)    / item_name (String)
  Resolution: add item_id + item_name; keep product_id/product_name for
  backward compatibility (they can be dropped in a later cleanup migration).
  Also add missing index ix_order_items_item_id.

TABLE: tables
  MISSING from both ORM and migration (referenced by routes):
    - qr_code_url   VARCHAR(500) NULL
    - qr_menu_url   VARCHAR(500) NULL
    - display_order INTEGER      NOT NULL DEFAULT 0
  Added to migration AND ORM model must be updated separately.

TABLE: areas
  MISSING from both ORM and migration (referenced by routes):
    - display_order INTEGER NOT NULL DEFAULT 0

TABLE: categories
  MISSING from migration (present in ORM):
    - image_url     VARCHAR(500) NULL
    - sort_order    INTEGER      NOT NULL DEFAULT 0
  NOTE: routes also reference display_order — ORM uses sort_order for this
        purpose; no separate display_order column is added.

TABLE: items
  MISSING from migration (present in ORM):
    - image_url     VARCHAR(500) NULL
    - sort_order    INTEGER      NOT NULL DEFAULT 0
  NOTE: same as categories — ORM uses sort_order; routes alias it as
        display_order at the API layer.
  Also add missing index ix_items_is_available (present in ORM __table_args__
  but absent from migration 001).

INDEX NOTES:
  ix_orders_table_id and ix_orders_area_id are created here (alongside the
  columns they support) and NOT in 002_performance_indexes.py.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # orders — add missing financial + operational columns
    # ------------------------------------------------------------------
    op.add_column(
        "orders",
        sa.Column(
            "order_type",
            sa.String(30),
            nullable=False,
            server_default=sa.text("'dine_in'"),
            comment="dine_in | takeaway | delivery",
        ),
    )
    op.add_column(
        "orders",
        sa.Column("payment_method", sa.String(50), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column(
            "subtotal",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "tax_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "service_charge",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "discount_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "orders",
        sa.Column("special_instructions", sa.Text(), nullable=True),
    )

    # Widen total_amount precision to match ORM (10,2 -> 12,2)
    op.alter_column(
        "orders",
        "total_amount",
        type_=sa.Numeric(12, 2),
        existing_type=sa.Numeric(10, 2),
        existing_nullable=False,
    )

    # Add indexes that are in ORM __table_args__ but absent from migration 001.
    # ix_orders_table_id and ix_orders_area_id are created here (not in 002).
    op.create_index("ix_orders_table_id", "orders", ["table_id"])
    op.create_index("ix_orders_area_id", "orders", ["area_id"])
    op.create_index("ix_orders_payment_status", "orders", ["payment_status"])

    # ------------------------------------------------------------------
    # order_items — add ORM-aligned columns (item_id / item_name)
    # The legacy product_id / product_name columns are retained for now.
    # ------------------------------------------------------------------
    op.add_column(
        "order_items",
        sa.Column(
            "item_id",
            sa.BigInteger(),
            nullable=True,  # nullable during migration; backfill then tighten
            comment="Denormalised item BigInteger ID — intentionally NOT a FK",
        ),
    )
    op.add_column(
        "order_items",
        sa.Column(
            "item_name",
            sa.String(200),
            nullable=True,  # nullable during migration; backfill then tighten
            comment="Denormalised item name snapshot at order time",
        ),
    )
    op.create_index("ix_order_items_item_id", "order_items", ["item_id"])

    # ------------------------------------------------------------------
    # tables — add qr_code_url, qr_menu_url, display_order
    # ------------------------------------------------------------------
    op.add_column(
        "tables",
        sa.Column("qr_code_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "tables",
        sa.Column("qr_menu_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "tables",
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # ------------------------------------------------------------------
    # areas — add display_order
    # ------------------------------------------------------------------
    op.add_column(
        "areas",
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # ------------------------------------------------------------------
    # categories — add image_url, sort_order
    # ------------------------------------------------------------------
    op.add_column(
        "categories",
        sa.Column("image_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "categories",
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # ------------------------------------------------------------------
    # items — add image_url, sort_order + missing index
    # ------------------------------------------------------------------
    op.add_column(
        "items",
        sa.Column("image_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "items",
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    # Present in Item.__table_args__ but missing from migration 001
    op.create_index("ix_items_is_available", "items", ["is_available"])


def downgrade() -> None:
    # ------------------------------------------------------------------
    # items
    # ------------------------------------------------------------------
    op.drop_index("ix_items_is_available", table_name="items")
    op.drop_column("items", "sort_order")
    op.drop_column("items", "image_url")

    # ------------------------------------------------------------------
    # categories
    # ------------------------------------------------------------------
    op.drop_column("categories", "sort_order")
    op.drop_column("categories", "image_url")

    # ------------------------------------------------------------------
    # areas
    # ------------------------------------------------------------------
    op.drop_column("areas", "display_order")

    # ------------------------------------------------------------------
    # tables
    # ------------------------------------------------------------------
    op.drop_column("tables", "display_order")
    op.drop_column("tables", "qr_menu_url")
    op.drop_column("tables", "qr_code_url")

    # ------------------------------------------------------------------
    # order_items
    # ------------------------------------------------------------------
    op.drop_index("ix_order_items_item_id", table_name="order_items")
    op.drop_column("order_items", "item_name")
    op.drop_column("order_items", "item_id")

    # ------------------------------------------------------------------
    # orders — drop indexes BEFORE dropping columns that back them
    # ------------------------------------------------------------------
    op.drop_index("ix_orders_payment_status", table_name="orders")
    op.drop_index("ix_orders_area_id", table_name="orders")
    op.drop_index("ix_orders_table_id", table_name="orders")
    op.alter_column(
        "orders",
        "total_amount",
        type_=sa.Numeric(10, 2),
        existing_type=sa.Numeric(12, 2),
        existing_nullable=False,
    )
    op.drop_column("orders", "special_instructions")
    op.drop_column("orders", "discount_amount")
    op.drop_column("orders", "service_charge")
    op.drop_column("orders", "tax_amount")
    op.drop_column("orders", "subtotal")
    op.drop_column("orders", "payment_method")
    op.drop_column("orders", "order_type")
