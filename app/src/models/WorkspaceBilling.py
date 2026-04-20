from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.models.Base import Base, BigIntPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.Workspace import Workspace


class WorkspaceBilling(BigIntPrimaryKeyMixin, Base):
    """
    One-to-one billing record for a workspace.

    Billing records are never soft-deleted; they are only updated in place.
    The unique constraint on workspace_id enforces the one-to-one relationship
    at the database level.
    """

    __tablename__ = "workspace_billing"

    __table_args__ = (
        UniqueConstraint("workspace_id", name="uq_workspace_billing_workspace_id"),
    )

    # --- Foreign key (one-to-one enforced by UNIQUE) ---
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    # --- Plan ---
    plan: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="free",
        server_default="free",
    )
    plan_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        server_default="active",
    )
    billing_cycle: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )

    # --- Billing contact ---
    billing_email: Mapped[Optional[str]] = mapped_column(
        String(254),
        nullable=True,
    )
    billing_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )

    # --- Billing address ---
    billing_address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    billing_city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    billing_state: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    billing_country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    billing_postal_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    billing_phone: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
    )

    # --- Tax / legal ---
    tax_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # --- Subscription ---
    subscription_id: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    subscription_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    subscription_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    trial_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --- Limits ---
    max_personas: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    max_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
    )

    # --- Audit ---
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

    # --- Relationships ---
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="billing",
        lazy="select",
    )
