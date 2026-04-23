"""
Order ORM model — line items table.

PK is `sino` (serial number), NOT `id`.
order_id references order_details.order_id (no enforced FK — intentional snapshot).
item_id has no FK — intentional snapshot of item at time of order.
"""

from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, EntityMixin


class Order(EntityMixin, Base):
    """A single line item within an order."""

    __tablename__ = "orders"

    __table_args__ = (
        Index("ix_orders_order_id", "order_id"),
        Index("ix_orders_workspace_id", "workspace_id"),
        Index("ix_orders_persona_id", "persona_id"),
        Index("ix_orders_item_id", "item_id"),
    )

    # PK is sino, not id
    sino: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    # Soft reference to order_details.order_id — no enforced FK
    order_id: Mapped[str] = mapped_column(String(50), nullable=False)

    # Snapshot — no FK enforced
    item_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="RESTRICT"),
        nullable=False,
    )
    persona_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("personas.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    persona: Mapped["Persona"] = relationship(  # noqa: F821
        "Persona",
        back_populates="orders",
        foreign_keys=[persona_id],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Order sino={self.sino} order_id={self.order_id!r} item={self.item_name!r}>"
