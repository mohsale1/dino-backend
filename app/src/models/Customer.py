"""
Customer ORM model.
No email column. Unique: (mobile, workspace_id).
"""

from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Customer(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A customer identified by mobile number within a workspace."""

    __tablename__ = "customers"

    __table_args__ = (
        UniqueConstraint("mobile", "workspace_id", name="uq_customers_mobile_workspace"),
        Index("ix_customers_workspace_id", "workspace_id"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    mobile: Mapped[str] = mapped_column(String(30), nullable=False)
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    persona_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(  # noqa: F821
        "Workspace",
        back_populates="customers",
        lazy="noload",
    )
    persona: Mapped[Optional["Persona"]] = relationship(  # noqa: F821
        "Persona",
        back_populates="customers",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} mobile={self.mobile!r}>"
