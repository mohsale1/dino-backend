"""
Customer ORM model.

A Customer is a walk-in guest identified only by name and mobile number.
They are scoped to a Workspace but have NO role, NO permission, and NO
link to application_users. They are created automatically when a public
order is placed with a mobile number that does not yet exist in the workspace.
"""
from typing import Optional
from sqlalchemy import BigInteger, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Customer(BigIntPrimaryKeyMixin, EntityMixin, Base):
    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    mobile: Mapped[str] = mapped_column(String(30), nullable=False)

    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    persona_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="customers", lazy="select")
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="customer",
        passive_deletes=True,
        lazy="select",
    )
    persona: Mapped[Optional["Persona"]] = relationship("Persona", back_populates="customers", lazy="select")

    __table_args__ = (
        UniqueConstraint("mobile", "workspace_id", name="uq_customers_mobile_workspace"),
        Index("ix_customers_mobile", "mobile"),
        Index("ix_customers_workspace_mobile", "workspace_id", "mobile"),  # fast lookup
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} name={self.name!r} mobile={self.mobile!r}>"
