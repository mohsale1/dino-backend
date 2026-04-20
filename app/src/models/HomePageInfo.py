"""
HomePageInfo ORM model.

This is a single-row configuration table (id is always 1).
JSONB columns store structured data for the public-facing landing page:
  - stats        : list of stat objects
  - testimonials : list of testimonial objects
  - contact      : contact information object

The table intentionally omits the standard UUID / soft-delete mixins because:
  - It uses a fixed INTEGER primary key (always 1).
  - It is never soft-deleted; it is only ever updated.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Integer, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.models.Base import Base


class HomePageInfo(Base):
    """Single-row landing-page configuration table."""

    __tablename__ = "homepage_info"

    # Fixed primary key — always 1
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
        server_default=text("1"),
        nullable=False,
    )

    # JSONB payload columns
    stats: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of stat objects shown on the landing page",
    )
    testimonials: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of customer testimonial objects",
    )
    contact: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Contact information object",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return "<HomePageInfo id=1>"
