"""
Category ORM model.
workspace_id removed — scoped via persona_id (CASCADE, NOT NULL).
"""

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Category(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A menu category."""

    __tablename__ = "categories"

    __table_args__ = (
        Index("ix_categories_persona_id", "persona_id"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    persona_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    items: Mapped[list["Item"]] = relationship(  # noqa: F821
        "Item",
        back_populates="category",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r}>"
