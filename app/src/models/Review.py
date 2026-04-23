"""
Review ORM model — customer reviews for personas within a workspace.
"""

from typing import Optional

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Index, SmallInteger, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Review(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A customer review submitted for a persona within a workspace."""

    __tablename__ = "reviews"

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating"),
        Index("ix_reviews_workspace_id", "workspace_id"),
        Index("ix_reviews_persona_id", "persona_id"),
        Index("ix_reviews_user_id", "user_id"),
        Index("ix_reviews_is_approved", "is_approved"),
        Index("ix_reviews_rating", "rating"),
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
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rating: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=5,
        server_default=text("5"),
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
    persona: Mapped[Optional["Persona"]] = relationship(  # noqa: F821
        "Persona",
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
