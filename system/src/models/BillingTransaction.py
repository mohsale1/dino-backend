"""
BillingTransaction ORM model — platform billing records (shared table).
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.models.Base import Base, BigIntPrimaryKeyMixin


class BillingTransaction(BigIntPrimaryKeyMixin, Base):
    """Platform billing transaction (subscription payments)."""

    __tablename__ = "billing_transactions"

    __table_args__ = (
        UniqueConstraint("invoice_number", name="uq_billing_transactions_invoice_number"),
        Index("ix_billing_transactions_workspace_id", "workspace_id"),
        Index("ix_billing_transactions_payment_status", "payment_status"),
    )

    workspace_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    plan: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'INR'"))
    billing_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    billing_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    payment_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending'")
    )
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    payment_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    last_paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, server_default=text("0"))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<BillingTransaction id={self.id} workspace_id={self.workspace_id} plan={self.plan!r}>"
