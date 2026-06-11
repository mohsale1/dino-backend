"""
Workspace ORM model and workspace_personas association table.
owner_id removed.
"""

from typing import Optional

from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, String, Table, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


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
        ForeignKey("personas.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)


# ---------------------------------------------------------------------------
# Workspace entity
# ---------------------------------------------------------------------------

class Workspace(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A tenant-level container."""

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    # Relationships
    billing: Mapped[Optional["WorkspaceBilling"]] = relationship(  # noqa: F821
        "WorkspaceBilling",
        back_populates="workspace",
        uselist=False,
        lazy="noload",
    )
    billing_details: Mapped[Optional["BillingDetail"]] = relationship(  # noqa: F821
        "BillingDetail",
        uselist=False,
        lazy="noload",
    )
    personas: Mapped[list["Persona"]] = relationship(  # noqa: F821
        "Persona",
        secondary="workspace_personas",
        primaryjoin="Workspace.id == workspace_personas.c.workspace_id",
        secondaryjoin="Persona.id == workspace_personas.c.persona_id",
        lazy="noload",
    )
    reviews: Mapped[list["Review"]] = relationship(  # noqa: F821
        "Review",
        back_populates="workspace",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} name={self.name!r}>"
