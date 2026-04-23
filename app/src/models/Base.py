"""
SQLAlchemy 2.x DeclarativeBase with shared mixins for dino-application.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Project-wide declarative base."""
    pass


class BigIntPrimaryKeyMixin:
    """Auto-incrementing BigInteger primary key (PostgreSQL BIGSERIAL)."""

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )


class EntityMixin:
    """
    Unified mixin that adds lifecycle and audit columns to every entity table.

    is_active=True  : record is live and visible.
    is_active=False : record is soft-deleted / inactive.
    """

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
