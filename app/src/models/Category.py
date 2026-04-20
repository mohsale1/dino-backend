"""
Category ORM model.

Categories are workspace-scoped and support a single level of nesting via the
self-referential parent_id foreign key.  Items belong to a Category.
"""

from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, EntityMixin, UUIDPrimaryKeyMixin


class Category(UUIDPrimaryKeyMixin, EntityMixin, Base):
    """Menu / product category with optional parent for sub-categories."""

    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
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

    # ------------------------------------------------------------------ #
    # Foreign keys                                                         #
    # ------------------------------------------------------------------ #
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Self-referential: optional parent category
    parent_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="children",
        lazy="select",
    )
    children: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent",
        lazy="select",
    )
    items: Mapped[list["Item"]] = relationship(  # noqa: F821
        "Item",
        back_populates="category",
        lazy="select",
    )

    # ------------------------------------------------------------------ #
    # Indexes                                                              #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index("ix_categories_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r}>"
