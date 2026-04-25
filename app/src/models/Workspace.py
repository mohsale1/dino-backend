"""
Workspace ORM model and workspace_personas association table (shared).
"""

from typing import Optional

from sqlalchemy import BigInteger, Column, ForeignKey, String, Table, Text
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

    owner_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    owner: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User",
        foreign_keys="[Workspace.owner_id]",
        lazy="noload",
    )
    billing: Mapped[Optional["WorkspaceBilling"]] = relationship(  # noqa: F821
        "WorkspaceBilling",
        back_populates="workspace",
        uselist=False,
        lazy="noload",
    )
    billing_details: Mapped[Optional["BillingDetail"]] = relationship(  # noqa: F821
        "BillingDetail",
        back_populates="workspace",
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
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        "User",
        foreign_keys="[User.workspace_id]",
        back_populates="workspace",
        lazy="noload",
    )
    customers: Mapped[list["Customer"]] = relationship(  # noqa: F821
        "Customer",
        back_populates="workspace",
        lazy="noload",
    )
    reviews: Mapped[list["Review"]] = relationship(  # noqa: F821
        "Review",
        back_populates="workspace",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} name={self.name!r}>"
