"""
User ORM model — unified users table (shared with dino-system).
workspace_id removed — app users are linked to workspaces via user_personas → workspace_personas.
email is globally unique.
user_type=1 for application users, 0 for system users.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, SmallInteger, String, Table, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


# ---------------------------------------------------------------------------
# Association table
# ---------------------------------------------------------------------------

user_personas = Table(
    "user_personas",
    Base.metadata,
    Column("user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("persona_id", BigInteger, ForeignKey("personas.id", ondelete="CASCADE"), primary_key=True),
)


class User(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """Unified user entity — application users have user_type=1."""

    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_email", "email"),
        Index("ix_users_user_type", "user_type"),
        Index("ix_users_role_id", "role_id"),
    )

    user_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("1"),
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
        "Role", back_populates="users", lazy="noload",
    )
    personas: Mapped[list["Persona"]] = relationship(  # noqa: F821
        "Persona", secondary="user_personas", back_populates="users", lazy="noload",
    )
    reviews: Mapped[list["Review"]] = relationship(  # noqa: F821
        "Review", back_populates="user", lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} type={self.user_type}>"
