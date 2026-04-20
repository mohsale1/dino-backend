"""
Role ORM model + role_permissions association table.

role_type:
    0 = System role  (managed by dino-system)
    1 = Application role (managed by dino-application)
"""

from typing import Optional

from sqlalchemy import (
    BigInteger,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, EntityMixin, UUIDPrimaryKeyMixin


# --------------------------------------------------------------------------- #
# Association table                                                            #
# --------------------------------------------------------------------------- #
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        BigInteger,
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "permission_id",
        BigInteger,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Index("ix_role_permissions_permission_id", "permission_id"),
)


# --------------------------------------------------------------------------- #
# Role model                                                                   #
# --------------------------------------------------------------------------- #
class Role(UUIDPrimaryKeyMixin, EntityMixin, Base):
    """A named role that groups permissions together."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role_type: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="0=System, 1=Application",
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    permissions: Mapped[list["Permission"]] = relationship(  # noqa: F821
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        lazy="select",
    )
    users: Mapped[list["ApplicationUser"]] = relationship(  # noqa: F821
        "ApplicationUser",
        back_populates="role",
        lazy="select",
    )

    # ------------------------------------------------------------------ #
    # Constraints & indexes                                                #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        UniqueConstraint("name", name="uq_roles_name"),
        Index("ix_roles_is_active", "is_active"),
        Index("ix_roles_role_type", "role_type"),
    )

    def __repr__(self) -> str:
        return f"<Role id={self.id} name={self.name!r} type={self.role_type}>"
