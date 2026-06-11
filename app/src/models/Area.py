"""
Area ORM model.
workspace_id removed — scoped entirely via persona_id.
persona_id FK is CASCADE (area deleted when persona is deleted).
"""

from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Area(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A seating/service area within a persona."""

    __tablename__ = "areas"

    __table_args__ = (
        Index("ix_areas_persona_id", "persona_id"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    persona_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    persona: Mapped["Persona"] = relationship(  # noqa: F821
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
