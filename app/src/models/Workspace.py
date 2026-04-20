"""
Workspace ORM model.

A Workspace is the top-level tenant entity.  Every other resource belongs to
a workspace.  Billing details are stored in a separate WorkspaceBilling table.
"""

from typing import Optional

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, EntityMixin, UUIDPrimaryKeyMixin


class Workspace(UUIDPrimaryKeyMixin, EntityMixin, Base):
    """Top-level tenant / workspace."""

    __tablename__ = "workspaces"

    # ------------------------------------------------------------------ #
    # Core identity                                                        #
    # ------------------------------------------------------------------ #
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ------------------------------------------------------------------ #
    # Owner reference (system_users.id is VARCHAR(4))                     #
    # ------------------------------------------------------------------ #
    owner_id: Mapped[Optional[str]] = mapped_column(
        String(4),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    billing: Mapped[Optional["WorkspaceBilling"]] = relationship(  # noqa: F821
        "WorkspaceBilling",
        back_populates="workspace",
        uselist=False,
        lazy="select",
    )
    personas: Mapped[list["Persona"]] = relationship(  # noqa: F821
        "Persona",
        secondary="workspace_personas",
        back_populates="workspaces",
        lazy="select",
    )
    users: Mapped[list["ApplicationUser"]] = relationship(  # noqa: F821
        "ApplicationUser",
        back_populates="workspace",
        lazy="select",
    )
    customers: Mapped[list["Customer"]] = relationship(  # noqa: F821
        "Customer",
        back_populates="workspace",
        lazy="select",
    )

    # ------------------------------------------------------------------ #
    # Indexes                                                              #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index("ix_workspaces_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} name={self.name!r}>"
