"""
HomePageInfo ORM model.

Single-row configuration table for the public-facing home page.
All content columns are JSONB for maximum flexibility.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.Base import Base, UUIDPrimaryKeyMixin, EntityMixin


class HomePageInfo(UUIDPrimaryKeyMixin, EntityMixin, Base):
    """
    Singleton configuration row for the public-facing home page.

    stats        – JSONB array of stat objects displayed on the home page
    testimonials – JSONB array of testimonial objects
    contact      – JSONB object with contact details (email, phone, address …)
    """

    __tablename__ = "homepage_info"

    stats: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        comment="Array of stat objects for the home page",
    )
    testimonials: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        comment="Array of testimonial objects",
    )
    contact: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="Contact information object",
    )

    def __repr__(self) -> str:
        return f"<HomePageInfo id={self.id}>"
