"""
BillingConfig ORM model — per-persona tax, service charge, discount and currency defaults.

One row per (workspace_id, persona_id) pair.
Rate columns use Numeric(5, 4): store 0.0500 to represent 5 %.
"""

from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class BillingConfig(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """Tax/service-charge/discount configuration scoped to a single persona."""

    __tablename__ = "billing_config"

    __table_args__ = (
        UniqueConstraint("workspace_id", "persona_id", name="uq_billing_config_workspace_persona"),
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 1", name="ck_billing_config_tax_rate"),
        CheckConstraint(
            "service_charge_rate >= 0 AND service_charge_rate <= 1",
            name="ck_billing_config_service_charge_rate",
        ),
        Index("ix_billing_config_workspace_id", "workspace_id"),
        Index("ix_billing_config_persona_id", "persona_id"),
    )

    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE", name="fk_billing_config_workspace_id"),
        nullable=False,
    )
    persona_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("personas.id", ondelete="CASCADE", name="fk_billing_config_persona_id"),
        nullable=False,
    )

    # Tax
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        server_default="0.0000",
        comment="Fractional rate: 0.0500 = 5 %",
    )
    tax_label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        server_default="Tax",
    )

    # Service charge
    service_charge_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        server_default="0.0000",
        comment="Fractional rate: 0.0500 = 5 %",
    )
    service_charge_label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        server_default="Service Charge",
    )

    # Discount
    discount_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        server_default="0.0000",
        comment="Fractional rate: 0.1000 = 10 %",
    )

    # Currency
    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default="INR",
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(  # noqa: F821
        "Workspace",
        lazy="noload",
    )
    persona: Mapped["Persona"] = relationship(  # noqa: F821
        "Persona",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<BillingConfig id={self.id} "
            f"workspace_id={self.workspace_id} "
            f"persona_id={self.persona_id} "
            f"tax_rate={self.tax_rate}>"
        )