"""
Workspace ORM model and workspace_personas association table.

owner_id       – references application_users in dino-application; no FK enforced.
workspace_personas – links workspaces to personas; persona_id has no FK because
                     Persona may live in a separate schema or service context.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, UUIDPrimaryKeyMixin, EntityMixin


# ---------------------------------------------------------------------------
# Association table
# ---------------------------------------------------------------------------

workspace_personas = Table(
    "workspace_personas",
    Base.metadata,
    Column(
        "workspace_id",
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "persona_id",
        BigInteger,
        primary_key=True,
        nullable=False,
        comment="References personas.id – no FK enforced (cross-service)",
    ),
    Index("ix_workspace_personas_persona_id", "persona_id"),
)


# ---------------------------------------------------------------------------
# Workspace entity
# ---------------------------------------------------------------------------

class Workspace(UUIDPrimaryKeyMixin, EntityMixin, Base):
    """
    A tenant-level container that groups Personas and holds billing info.

    owner_id
    --------
    BigInteger ID of the ApplicationUser who owns this workspace.  Stored
    without a DB-level FK because ApplicationUser lives in dino-application.

    referred_by
    -----------
    VARCHAR(10) FK → system_users.id  (nullable).  Tracks which SystemUser
    referred this workspace during registration.

    subscription_plan / subscription_status
    ----------------------------------------
    Free-text strings kept flexible for future plan additions.
    Defaults: plan='Free', status='Active'.
    """

    __tablename__ = "workspaces"

    __table_args__ = (
        Index("ix_workspaces_is_active", "is_active"),
        Index("ix_workspaces_subscription_status", "subscription_status"),
    )

    # --- Ownership -----------------------------------------------------------
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Cross-service – no FK enforced
    owner_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        index=True,
        comment="References application_users.id – no FK enforced (cross-service)",
    )

    referred_by: Mapped[Optional[str]] = mapped_column(
        String(10),
        ForeignKey("system_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # --- Billing contact -----------------------------------------------------
    billing_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    billing_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    billing_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    billing_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    billing_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    billing_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    billing_postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    billing_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # --- Subscription --------------------------------------------------------
    subscription_plan: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'Free'"),
    )
    subscription_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'Active'"),
    )
    subscription_start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_billing_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    mrr: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default=text("0"),
        comment="Monthly Recurring Revenue in base currency",
    )

    # --- Relationships -------------------------------------------------------
    referred_by_user: Mapped[Optional["SystemUser"]] = relationship(  # noqa: F821
        "SystemUser",
        foreign_keys=[referred_by],
        lazy="noload",
    )
    personas: Mapped[list["Persona"]] = relationship(  # noqa: F821
        "Persona",
        secondary="workspace_personas",
        primaryjoin="Workspace.id == workspace_personas.c.workspace_id",
        secondaryjoin="Persona.id == workspace_personas.c.persona_id",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} name={self.name!r}>"
