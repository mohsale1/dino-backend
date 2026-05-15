"""
CustomerSession ORM model — tracks a customer's active menu session.

Lifecycle: QR scan → menu load → cart → name/phone entry → checkout → order placed.
order_id is a soft reference to order_details.order_id (no enforced FK — intentional snapshot).
session_token is reserved for future stateless auth flows.
"""

from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class CustomerSession(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A single customer session initiated from a QR-code table scan."""

    __tablename__ = "customer_sessions"

    __table_args__ = (
        Index("ix_customer_sessions_workspace_id", "workspace_id"),
        Index("ix_customer_sessions_persona_id", "persona_id"),
        Index("ix_customer_sessions_customer_id", "customer_id"),
        Index("ix_customer_sessions_order_id", "order_id"),
        Index("ix_customer_sessions_table_id", "table_id"),
    )

    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE", name="fk_customer_sessions_workspace_id"),
        nullable=False,
    )
    persona_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("personas.id", ondelete="CASCADE", name="fk_customer_sessions_persona_id"),
        nullable=False,
    )
    customer_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("customers.id", ondelete="SET NULL", name="fk_customer_sessions_customer_id"),
        nullable=True,
    )

    # Soft reference to order_details.order_id — no enforced FK
    order_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    table_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("tables.id", ondelete="SET NULL", name="fk_customer_sessions_table_id"),
        nullable=True,
    )

    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Reserved for future stateless auth (e.g. signed JWT stored client-side)
    session_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship(  # noqa: F821
        "Workspace",
        lazy="noload",
    )
    persona: Mapped["Persona"] = relationship(  # noqa: F821
        "Persona",
        lazy="noload",
    )
    customer: Mapped[Optional["Customer"]] = relationship(  # noqa: F821
        "Customer",
        lazy="noload",
    )
    table: Mapped[Optional["Table"]] = relationship(  # noqa: F821
        "Table",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<CustomerSession id={self.id} "
            f"workspace_id={self.workspace_id} "
            f"persona_id={self.persona_id} "
            f"order_id={self.order_id!r} "
            f"is_active={self.is_active}>"
        )