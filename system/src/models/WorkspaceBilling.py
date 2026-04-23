"""
WorkspaceBilling ORM model.

One-to-one with Workspace. Holds plan and billing contact information.
No subscription_id, subscription_start/end, trial_end, mrr, max_personas, max_users, tax_id.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin


class WorkspaceBilling(BigIntPrimaryKeyMixin, Base):
    """Billing plan and contact information for a workspace."""

    __tablename__ = "workspace_billing"

    __table_args__ = (
        UniqueConstraint("workspace_id", name="uq_workspace_billing_workspace_id"),
        Index("ix_workspace_billing_plan_status", "plan_status"),
        Index("ix_workspace_billing_next_billing_date", "next_billing_date"),
    )

    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    plan: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'free'"),
    )
    plan_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'active'"),
    )
    billing_cycle: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    billing_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    billing_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    billing_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    billing_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    billing_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    billing_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    billing_postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    billing_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    next_billing_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(  # noqa: F821
        "Workspace",
        back_populates="billing",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<WorkspaceBilling id={self.id} workspace_id={self.workspace_id} plan={self.plan!r}>"
