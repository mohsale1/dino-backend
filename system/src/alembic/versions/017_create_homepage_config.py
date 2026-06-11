"""017_create_homepage_config

Revision ID: 017
Revises: 016
Create Date: 2026-05-19

Changes:
- Create homepage_config table (singleton row for public marketing page)
- Stores contact info + stat card metadata
- Live counts (workspaces, orders) are computed at query time, not stored
- Singleton enforced via UniqueConstraint on singleton_key = 'default'
- Seed one default row on upgrade
"""

import sqlalchemy as sa
from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "homepage_config",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("singleton_key", sa.String(16), nullable=False, server_default="default"),

        # Contact
        sa.Column("contact_email", sa.String(320), nullable=True),
        sa.Column("contact_phone", sa.String(30), nullable=True),
        sa.Column("contact_address", sa.String(500), nullable=True),
        sa.Column("contact_city", sa.String(100), nullable=True),
        sa.Column("contact_state", sa.String(100), nullable=True),
        sa.Column("contact_postal_code", sa.String(20), nullable=True),
        sa.Column("contact_country", sa.String(100), nullable=True),

        # Stat 1 — businesses
        sa.Column("stat_businesses_label", sa.String(100), nullable=False, server_default="Active Businesses"),
        sa.Column("stat_businesses_suffix", sa.String(10), nullable=False, server_default="+"),
        sa.Column("stat_businesses_icon", sa.String(100), nullable=False, server_default="business"),

        # Stat 2 — orders
        sa.Column("stat_orders_label", sa.String(100), nullable=False, server_default="Orders Processed"),
        sa.Column("stat_orders_suffix", sa.String(10), nullable=False, server_default="+"),
        sa.Column("stat_orders_icon", sa.String(100), nullable=False, server_default="shopping_cart"),

        # Stat 3 — satisfaction
        sa.Column("stat_satisfaction_label", sa.String(100), nullable=False, server_default="Customer Satisfaction"),
        sa.Column("stat_satisfaction_suffix", sa.String(10), nullable=False, server_default="%"),
        sa.Column("stat_satisfaction_icon", sa.String(100), nullable=False, server_default="thumb_up"),
        sa.Column("satisfaction", sa.SmallInteger(), nullable=False, server_default="98"),

        # Stat 4 — uptime
        sa.Column("stat_uptime_label", sa.String(100), nullable=False, server_default="Uptime"),
        sa.Column("stat_uptime_suffix", sa.String(10), nullable=False, server_default="%"),
        sa.Column("stat_uptime_icon", sa.String(100), nullable=False, server_default="cloud_done"),
        sa.Column("uptime", sa.String(10), nullable=False, server_default="99.9"),

        # EntityMixin columns
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(now() AT TIME ZONE 'Asia/Kolkata')")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(now() AT TIME ZONE 'Asia/Kolkata')")),

        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("singleton_key", name="uq_homepage_config_singleton"),
        sa.CheckConstraint("satisfaction >= 0 AND satisfaction <= 100", name="ck_homepage_satisfaction"),
        sa.CheckConstraint("uptime::numeric >= 0.0 AND uptime::numeric <= 100.0", name="ck_homepage_uptime"),
    )

    # Seed the single default row
    op.execute(
        """
        INSERT INTO homepage_config (
            singleton_key,
            contact_email, contact_phone, contact_address,
            contact_city, contact_state, contact_postal_code, contact_country,
            stat_businesses_label, stat_businesses_suffix, stat_businesses_icon,
            stat_orders_label, stat_orders_suffix, stat_orders_icon,
            stat_satisfaction_label, stat_satisfaction_suffix, stat_satisfaction_icon, satisfaction,
            stat_uptime_label, stat_uptime_suffix, stat_uptime_icon, uptime,
            is_active, created_at, updated_at
        ) VALUES (
            'default',
            'contact@dino-order.com', '+91 98765 43210', '123 Business Park',
            'Mumbai', 'Maharashtra', '400001', 'India',
            'Active Businesses', '+', 'business',
            'Orders Processed', '+', 'shopping_cart',
            'Customer Satisfaction', '%', 'thumb_up', 98,
            'Uptime', '%', 'cloud_done', '99.9',
            true, now(), now()
        )
        """
    )


def downgrade() -> None:
    op.drop_table("homepage_config")
