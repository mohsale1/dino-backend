"""
Persona ORM model.

workspace_id is stored but NOT enforced as a foreign key because the
Workspace entity lives in the same service; however, the relationship
is intentionally left as a plain column to allow cross-service flexibility
and to avoid tight coupling at the DB level when needed.
"""

from typing import Optional

from sqlalchemy import BigInteger, Boolean, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.Base import Base, UUIDPrimaryKeyMixin, EntityMixin


class Persona(UUIDPrimaryKeyMixin, EntityMixin, Base):
    """
    A persona that belongs to a Workspace.

    industry_type / order_type
    --------------------------
    Integer enumerations whose meaning is defined at the application layer.
    Default 0 = unspecified.

    is_open
    -------
    Indicates whether the persona is currently accepting orders / open
    for business.  Distinct from is_active (which controls soft-delete state).

    is_deactivated
    --------------
    Billing-level suspension flag.  Set to True when the persona is suspended
    due to billing issues.  Distinct from is_active (soft-delete) and is_open
    (business availability).
    """

    __tablename__ = "personas"

    __table_args__ = (
        Index("ix_personas_is_active", "is_active"),
        Index("ix_personas_industry_type", "industry_type"),
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Cross-service reference – no FK constraint enforced at DB level
    workspace_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        index=True,
        comment="References workspaces.id – no FK enforced (cross-service)",
    )

    industry_type: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        comment="Application-defined industry enumeration",
    )
    order_type: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        comment="Application-defined order-type enumeration",
    )
    is_open: Mapped[bool] = mapped_column(
        nullable=False,
        server_default=text("true"),
        comment="Whether the persona is open for business",
    )
    is_deactivated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment="Billing-level suspension flag; True means suspended due to billing",
    )

    def __repr__(self) -> str:
        return f"<Persona id={self.id} name={self.name!r}>"
