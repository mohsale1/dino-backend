"""
Item ORM model. No sort_order.
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Item(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A menu item."""

    __tablename__ = "items"

    __table_args__ = (
        Index("ix_items_workspace_id", "workspace_id"),
        Index("ix_items_category_id", "category_id"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    is_vegetarian: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    category: Mapped["Category"] = relationship(  # noqa: F821
        "Category",
        back_populates="items",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Item id={self.id} name={self.name!r} price={self.price}>"
