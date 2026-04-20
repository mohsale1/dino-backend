"""
SQLAlchemy 2.x DeclarativeBase with shared mixins.

Mixins
------
BigIntPrimaryKeyMixin - auto-incrementing BigInteger primary key (BIGSERIAL)
EntityMixin           - is_active flag + created_at / updated_at timestamps

Soft-delete convention
----------------------
is_active=True  : record is live and visible (active).
is_active=False : record has been soft-deleted / deactivated.

There is NO is_deleted, deleted_at, or restored_at column anywhere in the
schema.  All soft-delete logic is expressed exclusively through is_active.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Project-wide declarative base.  Alembic imports this directly."""
    pass


class BigIntPrimaryKeyMixin:
    """Auto-incrementing BigInteger primary key (PostgreSQL BIGSERIAL)."""

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )


# Backward-compatible alias
UUIDPrimaryKeyMixin = BigIntPrimaryKeyMixin


class EntityMixin:
    """
    Unified mixin applied to every persisted entity.

    Columns
    -------
    is_active  : bool
        True  -> record is active/visible.
        False -> record is soft-deleted/inactive.
        Never NULL; defaults to True on insert.
    created_at : datetime (tz-aware)
        Set once by the database at INSERT time; never changes.
    updated_at : datetime (tz-aware)
        Set by the database at INSERT and refreshed automatically on every
        UPDATE via the onupdate hook.
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
