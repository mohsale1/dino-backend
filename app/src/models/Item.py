"""
Item ORM model.

An Item is a menu / product entry that belongs to a Category and a Workspace.
The is_vegetarian flag is tri-state: True = Veg, False = Non-Veg, None = N/A.
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, EntityMixin, UUIDPrimaryKeyMixin


class Item(UUIDPrimaryKeyMixin, EntityMixin, Base):
    """A single menu / product item."""

    __tablename__ = "items"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    # Tri-state: True=Veg, False=Non-Veg, None=Not Applicable
    is_vegetarian: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # ------------------------------------------------------------------ #
    # Foreign keys                                                         #
    # ------------------------------------------------------------------ #
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    category: Mapped["Category"] = relationship(  # noqa: F821
        "Category",
        back_populates="items",
        lazy="select",
    )

    # ------------------------------------------------------------------ #
    # Indexes                                                              #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index("ix_items_is_active", "is_active"),
        Index("ix_items_is_available", "is_available"),
    )

    def __repr__(self) -> str:
        return f"<Item id={self.id} name={self.name!r} price={self.price}>"
