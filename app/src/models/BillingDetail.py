"""
BillingDetail ORM model — GST/tax billing details for a workspace.
No address_line2.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.models.Base import Base, BigIntPrimaryKeyMixin


class BillingDetail(BigIntPrimaryKeyMixin, Base):
    """Legal/tax billing details for a workspace."""

    __tablename__ = "billing_details"

    __table_args__ = (
        UniqueConstraint("workspace_id", name="uq_billing_details_workspace_id"),
        Index("ix_billing_details_workspace_id", "workspace_id"),
    )

    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    legal_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    trade_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    gstin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pan: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    billing_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    billing_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    address_line1: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    workspace: Mapped["Workspace"] = relationship(  # noqa: F821
        "Workspace",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<BillingDetail id={self.id} workspace_id={self.workspace_id}>"
