"""
Review ORM model — customer reviews for a workspace.
No persona_id. Rating is Numeric(3,1) to support half-star values (e.g. 4.5).
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Index, Numeric, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Review(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A customer review submitted for a workspace."""

    __tablename__ = "reviews"

    __table_args__ = (
        CheckConstraint("rating >= 0.5 AND rating <= 5.0", name="ck_reviews_rating"),
        Index("ix_reviews_workspace_id", "workspace_id"),
        Index("ix_reviews_user_id", "user_id"),
        Index("ix_reviews_is_approved", "is_approved"),
        Index("ix_reviews_rating", "rating"),
        # One review per authenticated user per workspace (partial — anonymous allowed)
        Index(
            "uq_reviews_workspace_user",
            "workspace_id", "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
    )

    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 1),
        nullable=False,
        default=Decimal("5.0"),
        server_default=text("5.0"),
    )
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_approved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(  # noqa: F821
        "Workspace",
        back_populates="reviews",
        lazy="noload",
    )
    user: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User",
        back_populates="reviews",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Review id={self.id} workspace_id={self.workspace_id} rating={self.rating}>"
