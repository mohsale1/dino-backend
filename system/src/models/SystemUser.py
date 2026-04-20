"""
SystemUser ORM model.

Primary key is a VARCHAR(4) 4-digit numeric string in the range '1000'–'9999'.
This is intentional — it is NOT a UUID.

Deletion strategy: there is no soft-delete on system_users.
When a user is deleted, is_active is set to False.
The record is never hidden or removed — it remains fully visible.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base


class SystemUser(Base):
    """An internal (back-office) user of the dino-system service."""

    __tablename__ = "system_users"

    __table_args__ = (
        Index("ix_system_users_email", "email"),
        Index("ix_system_users_role_id", "role_id"),
    )

    # --- Primary key (VARCHAR 4, NOT UUID) -----------------------------------
    id: Mapped[str] = mapped_column(
        String(4),
        primary_key=True,
        comment="4-digit numeric string, range 1000-9999",
    )

    # --- Identity fields -----------------------------------------------------
    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        unique=True,
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # --- Role FK -------------------------------------------------------------
    role_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # --- Status --------------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        comment="False means the user has been deactivated or deleted",
    )

    # --- Session tracking ----------------------------------------------------
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --- Audit ---------------------------------------------------------------
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

    # --- Relationships -------------------------------------------------------
    role: Mapped["Role"] = relationship(  # noqa: F821
        "Role",
        back_populates="system_users",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<SystemUser id={self.id!r} email={self.email!r}>"
