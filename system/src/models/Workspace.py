"""
Workspace ORM model and workspace_personas association table.

owner_id    â€“ references users.id (SET NULL on delete)
is_verified â€“ set to True when an admin approves the workspace request
No billing columns â€” billing is in workspace_billing table.
"""

from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    text,
)
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
    Index("ix_workspace_personas_persona_id", "persona_id"),
)


# ---------------------------------------------------------------------------
# Workspace entity
# ---------------------------------------------------------------------------

class Workspace(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A tenant-level container that groups Personas and holds billing info."""

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    owner_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="Set to true when an admin approves the workspace request",
    )

    # Relationships
    owner: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User",
        foreign_keys=[owner_id],
        lazy="noload",
    )
    billing: Mapped[Optional["WorkspaceBilling"]] = relationship(  # noqa: F821
        "WorkspaceBilling",
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

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} name={self.name!r} verified={self.is_verified}>"

