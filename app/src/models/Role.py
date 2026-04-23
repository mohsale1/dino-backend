"""
Role ORM model and role_permissions association table (shared with dino-system).
"""

from typing import Optional

from sqlalchemy import BigInteger, Column, ForeignKey, Index, SmallInteger, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


# ---------------------------------------------------------------------------
# Association table
# ---------------------------------------------------------------------------

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
)


class Role(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A named role that groups permissions together."""

    __tablename__ = "roles"

    __table_args__ = (
        UniqueConstraint("name", name="uq_roles_name"),
        Index("ix_roles_role_type", "role_type"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role_type: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="0=System, 1=Application",
    )

    # Relationships
    permissions: Mapped[list["Permission"]] = relationship(  # noqa: F821
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Role id={self.id} name={self.name!r} type={self.role_type}>"
