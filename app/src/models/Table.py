"""
Table ORM model.
workspace_id removed — scoped via persona_id (CASCADE, NOT NULL).
Unique: (area_id, table_number).
"""

from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Table(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A physical table within an area."""

    __tablename__ = "tables"

    __table_args__ = (
        UniqueConstraint("area_id", "table_number", name="uq_tables_area_table_number"),
        Index("ix_tables_area_id", "area_id"),
        Index("ix_tables_persona_id", "persona_id"),
    )

    table_number: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("4"))
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'available'"),
        comment="available | occupied | reserved | out_of_service",
    )
    area_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("areas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    persona_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    area: Mapped["Area"] = relationship(  # noqa: F821
        "Area",
        back_populates="tables",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Table id={self.id} number={self.table_number!r} status={self.status!r}>"
