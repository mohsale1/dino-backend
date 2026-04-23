"""
Persona ORM model.

persona_type:
    0 = Food
    1 = NonFood

order_type:
    0 = Online
    1 = Manual

is_open        – whether the persona is currently open for business.
is_deactivated – billing-level suspension flag.
"""

from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, SmallInteger, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Persona(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A persona (outlet/branch) that belongs to a Workspace."""

    __tablename__ = "personas"

    __table_args__ = (
        Index("ix_personas_persona_type", "persona_type"),
        Index("ix_personas_workspace_id", "workspace_id"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    persona_type: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="0=Food, 1=NonFood",
    )
    order_type: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="0=Online, 1=Manual",
    )

    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)

    is_open: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        comment="Whether the persona is open for business",
    )
    is_deactivated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment="Billing-level suspension flag",
    )

    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(  # noqa: F821
        "Workspace",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Persona id={self.id} name={self.name!r}>"
