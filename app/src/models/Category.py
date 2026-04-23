"""
Category ORM model. No sort_order, no parent_id.
"""

from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Category(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A menu category."""

    __tablename__ = "categories"

    __table_args__ = (
        Index("ix_categories_workspace_id", "workspace_id"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
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
    items: Mapped[list["Item"]] = relationship(  # noqa: F821
        "Item",
        back_populates="category",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r}>"
