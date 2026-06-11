"""
Persona ORM model.
workspace_id removed — workspace association is via workspace_personas join table.

persona_type: 0=Food, 1=NonFood
order_type:   0=Online, 1=Manual
is_open        — whether the persona is currently open for business.
is_deactivated — billing-level suspension flag.
"""

from typing import Optional

from sqlalchemy import Boolean, Index, SmallInteger, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Persona(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A persona (outlet/branch) linked to workspaces via workspace_personas."""

    __tablename__ = "personas"

    __table_args__ = (
        Index("ix_personas_persona_type", "persona_type"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    persona_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default=text("0"),
        comment="0=Food, 1=NonFood",
    )
    order_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default=text("0"),
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
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_deactivated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    # Relationships
    workspace: Mapped[Optional["Workspace"]] = relationship(  # noqa: F821
        "Workspace",
        secondary="workspace_personas",
        primaryjoin="Persona.id == workspace_personas.c.persona_id",
        secondaryjoin="Workspace.id == workspace_personas.c.workspace_id",
        uselist=False,
        lazy="noload",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<Persona id={self.id} name={self.name!r}>"
