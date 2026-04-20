"""
Persona ORM model + workspace_personas association table.

A Persona represents a single outlet / branch.  It can belong to one or
more Workspaces via the workspace_personas many-to-many table.

persona_type:
    0 = FOOD
    1 = NON_FOOD

order_type:
    0 = Online
    1 = Manual (Counter)
"""

from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, EntityMixin, UUIDPrimaryKeyMixin


# --------------------------------------------------------------------------- #
# Association table                                                            #
# --------------------------------------------------------------------------- #
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
        ForeignKey("personas.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)


# --------------------------------------------------------------------------- #
# Persona model                                                                #
# --------------------------------------------------------------------------- #
class Persona(UUIDPrimaryKeyMixin, EntityMixin, Base):
    """A single outlet / branch belonging to one or more workspaces."""

    __tablename__ = "personas"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    persona_type: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="0=FOOD, 1=NON_FOOD",
    )
    order_type: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="0=Online, 1=Manual",
    )
    is_open: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    # Billing suspension flag — ONLY on Persona, not on any other model
    is_deactivated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)

    # Primary workspace (denormalised for fast lookups)
    workspace_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    workspaces: Mapped[list["Workspace"]] = relationship(  # noqa: F821
        "Workspace",
        secondary="workspace_personas",
        back_populates="personas",
        lazy="select",
    )
    areas: Mapped[list["Area"]] = relationship(  # noqa: F821
        "Area",
        back_populates="persona",
        lazy="select",
    )
    customers: Mapped[list["Customer"]] = relationship(  # noqa: F821
        "Customer",
        back_populates="persona",
        lazy="select",
    )
    users: Mapped[list["ApplicationUser"]] = relationship(  # noqa: F821
        "ApplicationUser",
        secondary="user_personas",
        back_populates="personas",
        lazy="select",
    )
    orders: Mapped[list["Order"]] = relationship(  # noqa: F821
        "Order",
        back_populates="persona",
        lazy="select",
    )
    reviews: Mapped[list["Review"]] = relationship(  # noqa: F821
        "Review",
        back_populates="persona",
        lazy="select",
    )

    # ------------------------------------------------------------------ #
    # Indexes                                                              #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index("ix_personas_is_active", "is_active"),
        Index("ix_personas_persona_type", "persona_type"),
    )

    def __repr__(self) -> str:
        return f"<Persona id={self.id} name={self.name!r}>"
