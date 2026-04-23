"""
OrderTransaction ORM model — payment record for an order.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text

from src.models.Base import Base, BigIntPrimaryKeyMixin


class OrderTransaction(BigIntPrimaryKeyMixin, Base):
    """Payment transaction for an order."""

    __tablename__ = "order_transactions"

    __table_args__ = (
        Index("ix_order_transactions_order_id", "order_id"),
        Index("ix_order_transactions_workspace_id", "workspace_id"),
    )

    order_id: Mapped[str] = mapped_column(String(50), nullable=False)
    customer_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    workspace_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    persona_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("personas.id", ondelete="RESTRICT"), nullable=False
    )
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default="0")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default="0")
    currency: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'INR'"))
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    payment_status: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'unpaid'"))
    payment_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship("Customer", lazy="noload")  # noqa: F821

    def __repr__(self) -> str:
        return f"<OrderTransaction id={self.id} order_id={self.order_id!r} status={self.payment_status!r}>"
