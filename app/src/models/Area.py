"""
Area ORM model.

An Area represents a physical section of an outlet (e.g. "Ground Floor",
"Rooftop", "Drive-Through").  Areas belong to a Persona and a Workspace.
Tables are nested inside Areas.
"""

from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, EntityMixin, UUIDPrimaryKeyMixin


class Area(UUIDPrimaryKeyMixin, EntityMixin, Base):
    """A physical section / zone within a persona."""

    __tablename__ = "areas"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    display_order: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )

    # ------------------------------------------------------------------ #
    # Foreign keys                                                         #
    # ------------------------------------------------------------------ #
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    persona_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    persona: Mapped[Optional["Persona"]] = relationship(  # noqa: F821
        "Persona",
        back_populates="areas",
        lazy="select",
    )
    tables: Mapped[list["Table"]] = relationship(  # noqa: F821
        "Table",
        back_populates="area",
        lazy="select",
    )
    orders: Mapped[list["Order"]] = relationship(  # noqa: F821
        "Order",
        back_populates="area",
        lazy="select",
    )

    # ------------------------------------------------------------------ #
    # Indexes                                                              #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index("ix_areas_is_active", "is_active"),
        Index("ix_areas_workspace_persona", "workspace_id", "persona_id"),
    )

    def __repr__(self) -> str:
        return f"<Area id={self.id} name={self.name!r}>"
