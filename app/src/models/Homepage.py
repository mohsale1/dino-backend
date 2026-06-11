"""
HomepageConfig ORM model — singleton row that drives the public marketing page.

Contact details and stat card metadata (labels, suffixes, icons) are stored here
and editable from the UI. Live counts (workspaces, orders) are always computed
from the actual tables at query time — never stored here.

Singleton enforcement: UniqueConstraint on the constant column `singleton_key`
which is always 'default'. Only one row can ever exist.
"""

from typing import Optional

from sqlalchemy import CheckConstraint, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class HomepageConfig(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """Singleton configuration row for the public homepage."""

    __tablename__ = "homepage_config"

    __table_args__ = (
        UniqueConstraint("singleton_key", name="uq_homepage_config_singleton"),
        CheckConstraint("satisfaction >= 0 AND satisfaction <= 100", name="ck_homepage_satisfaction"),
        CheckConstraint("uptime >= 0.0 AND uptime <= 100.0", name="ck_homepage_uptime"),
    )

    # Singleton guard — always 'default', enforced by unique constraint
    singleton_key: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="default",
        server_default="default",
    )

    # ---------------------------------------------------------------------------
    # Contact info
    # ---------------------------------------------------------------------------
    contact_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    contact_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    contact_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    contact_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ---------------------------------------------------------------------------
    # Stat card metadata (live counts come from DB at query time)
    # ---------------------------------------------------------------------------

    # Stat 1 — active businesses (count from workspaces table)
    stat_businesses_label: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="Active Businesses"
    )
    stat_businesses_suffix: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="+"
    )
    stat_businesses_icon: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="business"
    )

    # Stat 2 — orders processed (count from order_details table)
    stat_orders_label: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="Orders Processed"
    )
    stat_orders_suffix: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="+"
    )
    stat_orders_icon: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="shopping_cart"
    )

    # Stat 3 — customer satisfaction (static percentage, editable)
    stat_satisfaction_label: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="Customer Satisfaction"
    )
    stat_satisfaction_suffix: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="%"
    )
    stat_satisfaction_icon: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="thumb_up"
    )
    satisfaction: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="98"
    )

    # Stat 4 — uptime (static percentage, editable)
    stat_uptime_label: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="Uptime"
    )
    stat_uptime_suffix: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="%"
    )
    stat_uptime_icon: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="cloud_done"
    )
    uptime: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="99.9"
    )

    def __repr__(self) -> str:
        return f"<HomepageConfig id={self.id} city={self.contact_city!r}>"
