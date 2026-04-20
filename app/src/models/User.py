"""
ApplicationUser ORM model.

Application users are workspace-scoped staff members (managers, cashiers, etc.).
They are distinct from system_users (dino-system service) which use VARCHAR(4) IDs.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, EntityMixin, UUIDPrimaryKeyMixin

# ------------------------------------------------------------------ #
# Association table                                                    #
# ------------------------------------------------------------------ #
user_personas = Table(
    "user_personas",
    Base.metadata,
    Column(
        "user_id",
        BigInteger,
        ForeignKey("application_users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "persona_id",
        BigInteger,
        ForeignKey("personas.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class ApplicationUser(UUIDPrimaryKeyMixin, EntityMixin, Base):
    """Staff / application-level user scoped to a workspace."""

    __tablename__ = "application_users"

    # ------------------------------------------------------------------ #
    # Identity                                                             #
    # ------------------------------------------------------------------ #
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ------------------------------------------------------------------ #
    # Foreign keys                                                         #
    # ------------------------------------------------------------------ #
    role_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    role: Mapped["Role"] = relationship(  # noqa: F821
        "Role",
        back_populates="users",
        lazy="select",
    )
    workspace: Mapped["Workspace"] = relationship(  # noqa: F821
        "Workspace",
        back_populates="users",
        lazy="select",
    )
    personas: Mapped[list["Persona"]] = relationship(  # noqa: F821
        "Persona",
        secondary="user_personas",
        back_populates="users",
        lazy="select",
    )

    # ------------------------------------------------------------------ #
    # Indexes & constraints                                                #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        UniqueConstraint("email", "workspace_id", name="uq_application_users_email_workspace"),
        Index("ix_application_users_is_active", "is_active"),
        Index("ix_application_users_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<ApplicationUser id={self.id} email={self.email!r}>"
