"""
Area ORM model. No display_order column.
"""

from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Area(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A seating/service area within a persona."""

    __tablename__ = "areas"

    __table_args__ = (
        Index("ix_areas_workspace_id", "workspace_id"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    persona_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    persona: Mapped[Optional["Persona"]] = relationship(  # noqa: F821
        "Persona",
        back_populates="areas",
        lazy="noload",
    )
    tables: Mapped[list["Table"]] = relationship(  # noqa: F821
        "Table",
        back_populates="area",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Area id={self.id} name={self.name!r}>"
