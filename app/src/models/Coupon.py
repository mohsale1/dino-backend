"""
Coupon ORM model.

Coupons are workspace-scoped discount codes.  The composite unique constraint
on (code, workspace_id) allows the same code string to exist in different
workspaces while remaining unique within each one.

discount_type: 'percentage' | 'fixed'
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.models.Base import Base, UUIDPrimaryKeyMixin, EntityMixin


class Coupon(UUIDPrimaryKeyMixin, EntityMixin, Base):
    """A discount coupon scoped to a workspace."""

    __tablename__ = "coupons"

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    discount_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="percentage | fixed",
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_discount_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    min_order_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    usage_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    usage_limit_per_user: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    # ------------------------------------------------------------------ #
    # Foreign keys                                                         #
    # ------------------------------------------------------------------ #
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Constraints & indexes                                                #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        UniqueConstraint("code", "workspace_id", name="uq_coupons_code_workspace"),
        Index("ix_coupons_is_active", "is_active"),
        Index("ix_coupons_is_available", "is_available"),
        Index("ix_coupons_valid_until", "valid_until"),
    )

    def __repr__(self) -> str:
        return f"<Coupon id={self.id} code={self.code!r} type={self.discount_type!r}>"
