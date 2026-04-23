"""
User ORM model — unified users table replacing both system_users and application_users.

user_type:
    0 = System user  (dino-system back-office staff)
    1 = Application user (workspace tenant staff)

workspace_id is NULL for system users (user_type=0).
Unique constraint: (email, workspace_id) — system users are globally unique by email,
application users are unique per workspace.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, SmallInteger, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class User(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """Unified user entity for both system and application users."""

    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint("email", "workspace_id", name="uq_users_email_workspace"),
        Index("ix_users_email", "email"),
        Index("ix_users_workspace_id", "workspace_id"),
        Index("ix_users_user_type", "user_type"),
        Index("ix_users_role_id", "role_id"),
    )

    user_type: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="0=System, 1=Application",
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    role_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    workspace_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        comment="NULL for system users (user_type=0)",
    )

    # Relationships
    role: Mapped["Role"] = relationship(  # noqa: F821
        "Role",
        back_populates="users",
        lazy="selectin",
    )
    workspace: Mapped[Optional["Workspace"]] = relationship(  # noqa: F821
        "Workspace",
        back_populates="users",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} type={self.user_type}>"
