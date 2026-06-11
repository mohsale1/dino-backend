"""
User ORM model — unified users table.
workspace_id removed — email is globally unique.
user_type: 0=System, 1=Application.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, SmallInteger, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class User(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """Unified user entity for both system and application users."""

    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_email", "email"),
        Index("ix_users_user_type", "user_type"),
        Index("ix_users_role_id", "role_id"),
    )

    user_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0",
        comment="0=System, 1=Application",
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False,
    )

    # Relationships
    role: Mapped["Role"] = relationship(  # noqa: F821
        "Role", back_populates="users", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} type={self.user_type}>"
