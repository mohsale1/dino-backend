"""
Permission ORM model (shared with dino-system).
No name, codename, description, or is_system columns.
"""

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Permission(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """Represents a discrete action that can be granted to a Role."""

    __tablename__ = "permissions"

    __table_args__ = (
        UniqueConstraint(
            "category", "resource", "action",
            name="uq_permissions_category_resource_action",
        ),
        Index("ix_permissions_category", "category"),
        Index("ix_permissions_resource", "resource"),
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="'system' or 'application'",
    )
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    roles: Mapped[list["Role"]] = relationship(  # noqa: F821
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Permission id={self.id} {self.category}:{self.resource}:{self.action}>"
