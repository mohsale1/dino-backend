"""
Customer ORM model.
workspace_id and persona_id removed.
mobile is globally unique across the table.
"""

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.Base import Base, BigIntPrimaryKeyMixin, EntityMixin


class Customer(BigIntPrimaryKeyMixin, EntityMixin, Base):
    """A customer identified by their mobile number."""

    __tablename__ = "customers"

    __table_args__ = (
        UniqueConstraint("mobile", name="uq_customers_mobile"),
        Index("ix_customers_mobile", "mobile"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    mobile: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"<Customer id={self.id} mobile={self.mobile!r}>"
