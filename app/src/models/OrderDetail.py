"""
OrderDetail ORM model — the order header/summary record.
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class OrderDetail(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """Order header — one record per order."""

    __tablename__ = "order_details"

    __table_args__ = (
        Index("ix_order_details_order_id", "order_id"),
        Index("ix_order_details_workspace_id", "workspace_id"),
        Index("ix_order_details_persona_id", "persona_id"),
        Index("ix_order_details_status", "status"),
    )

    order_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    order_type: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'dine_in'")
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending'")
    )
    customer_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    table_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("tables.id", ondelete="SET NULL"), nullable=True
    )
    area_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("areas.id", ondelete="SET NULL"), nullable=True
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    service_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=text("'INR'")
    )
    special_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    workspace_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    persona_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("personas.id", ondelete="RESTRICT"), nullable=False
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship("Customer", lazy="noload", viewonly=True)  # noqa: F821
    table: Mapped[Optional["Table"]] = relationship("Table", lazy="noload", viewonly=True)  # noqa: F821
    area: Mapped[Optional["Area"]] = relationship("Area", lazy="noload", viewonly=True)  # noqa: F821
    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="noload", viewonly=True)  # noqa: F821
    persona: Mapped["Persona"] = relationship(  # noqa: F821
        "Persona", back_populates="order_details", lazy="noload"
    )
    created_by_user: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User", foreign_keys=[created_by], lazy="noload", viewonly=True
    )
    order_items: Mapped[list["Order"]] = relationship(  # noqa: F821
        "Order",
        primaryjoin="OrderDetail.order_id == foreign(Order.order_id)",
        lazy="noload",
        viewonly=True,
    )
    transaction: Mapped[Optional["OrderTransaction"]] = relationship(  # noqa: F821
        "OrderTransaction",
        primaryjoin="OrderDetail.order_id == foreign(OrderTransaction.order_id)",
        uselist=False,
        lazy="noload",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<OrderDetail id={self.id} order_id={self.order_id!r} status={self.status!r}>"
