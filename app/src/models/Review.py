"""
Review ORM model.

Reviews are submitted by customers and are scoped to a Workspace and
optionally a Persona.  An admin approval flag (is_approved) controls
public visibility.
"""

from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, UUIDPrimaryKeyMixin, EntityMixin


class Review(UUIDPrimaryKeyMixin, EntityMixin, Base):
    """A customer review / testimonial."""

    __tablename__ = "reviews"

    reviewer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    reviewer_email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)
    reviewer_role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewer_avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_approved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
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
    persona_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    persona: Mapped[Optional["Persona"]] = relationship(  # noqa: F821
        "Persona",
        back_populates="reviews",
        lazy="select",
    )

    # ------------------------------------------------------------------ #
    # Indexes                                                              #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index("ix_reviews_is_active", "is_active"),
        Index("ix_reviews_is_approved", "is_approved"),
    )

    def __repr__(self) -> str:
        return f"<Review id={self.id} reviewer={self.reviewer_name!r} rating={self.rating}>"
