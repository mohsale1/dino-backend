from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class WorkspaceRequest(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """Workspace access request submitted by a user for a given workspace."""

    __tablename__ = "workspace_requests"

    __table_args__ = (
        Index("ix_workspace_requests_referred_by", "referred_by"),
        Index("ix_workspace_requests_workspace_id", "workspace_id"),
        Index("ix_workspace_requests_status", "status"),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    referred_by: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        comment="pending/approved/rejected",
    )
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    referred_by_user: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User",
        foreign_keys=[referred_by],
        lazy="noload",
    )
    workspace: Mapped["Workspace"] = relationship(  # noqa: F821
        "Workspace",
        lazy="noload",
    )
    reviewer: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User",
        foreign_keys=[reviewed_by],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<WorkspaceRequest id={self.id} email={self.email!r} status={self.status!r}>"
