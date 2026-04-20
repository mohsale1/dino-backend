"""
Permission ORM model.

Permissions are global (not scoped to a workspace) and are assigned to Roles
via the role_permissions association table defined in Role.py.
"""

from typing import Optional

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, EntityMixin, UUIDPrimaryKeyMixin


class Permission(UUIDPrimaryKeyMixin, EntityMixin, Base):
    """A single, named permission (e.g. 'orders:read')."""

    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    codename: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resource: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)   # e.g. 'orders'
    action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)      # e.g. 'read'

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    roles: Mapped[list["Role"]] = relationship(  # noqa: F821
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
        lazy="select",
    )

    # ------------------------------------------------------------------ #
    # Indexes                                                              #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        Index("ix_permissions_is_active", "is_active"),
        Index("ix_permissions_resource", "resource"),
    )

    def __repr__(self) -> str:
        return f"<Permission id={self.id} codename={self.codename!r}>"
