"""
Permission ORM model.
"""

from typing import Optional

from sqlalchemy import Boolean, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, UUIDPrimaryKeyMixin, EntityMixin


class Permission(UUIDPrimaryKeyMixin, EntityMixin, Base):
    """
    Represents a discrete action that can be granted to a Role.

    Columns
    -------
    name        – unique machine-readable identifier  (e.g. "workspace:read")
    description – human-readable explanation (nullable)
    category    – scope of the permission: 'system' | 'application'
    resource    – the resource this permission targets (e.g. "workspace")
    action      – the action being permitted (e.g. "read", "write", "delete")
    is_system   – True for built-in permissions that cannot be removed
    """

    __tablename__ = "permissions"

    __table_args__ = (
        Index("ix_permissions_is_active", "is_active"),
        Index("ix_permissions_category", "category"),
        Index("ix_permissions_resource", "resource"),
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="'system' or 'application'",
    )
    resource: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    # Relationships
    roles: Mapped[list["Role"]] = relationship(  # noqa: F821
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Permission id={self.id} name={self.name!r}>"
