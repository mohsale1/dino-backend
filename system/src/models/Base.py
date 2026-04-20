"""
SQLAlchemy 2.x DeclarativeBase with shared mixins for dino-system.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Project-wide declarative base. Alembic imports this."""
    pass


class BigIntPrimaryKeyMixin:
    """Auto-incrementing BigInteger primary key (PostgreSQL BIGSERIAL)."""

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        init=False,
    )


# Backward-compatible alias
UUIDPrimaryKeyMixin = BigIntPrimaryKeyMixin


class EntityMixin:
    """
    Unified mixin that adds lifecycle and audit columns to every entity table.

    Soft-delete convention
    ----------------------
    There is NO ``is_deleted`` column.  Soft-deletion is expressed solely
    through ``is_active``:

    * ``is_active = True``  – record is live and visible (default).
    * ``is_active = False`` – record is soft-deleted / inactive and should
                              be excluded from normal queries.

    Columns
    -------
    is_active   – active/soft-delete flag; NOT NULL, defaults to ``true``
                  on the database side; indexed for fast filtered queries.
    created_at  – set once by the DB on INSERT; NOT NULL.
    updated_at  – refreshed by the DB on every UPDATE; nullable.
    """

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )
