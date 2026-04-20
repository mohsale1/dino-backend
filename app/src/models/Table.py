"""
Table ORM model.

A Table is a physical dining table inside an Area.  The status column tracks
real-time occupancy.

status values: available | occupied | reserved | maintenance
"""

from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.Base import Base, EntityMixin, UUIDPrimaryKeyMixin


class Table(UUIDPrimaryKeyMixin, EntityMixin, Base):
    """A physical dining table within an area."""

    __tablename__ = "tables"

    table_number: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=4, server_default="4")
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="available",
        server_default="available",
        comment="available | occupied | reserved | maintenance",
    )
    qr_code_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    qr_menu_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    # ------------------------------------------------------------------ #
    # Foreign keys                                                         #
    # ------------------------------------------------------------------ #
    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    area_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("areas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    area: Mapped["Area"] = relationship(  # noqa: F821
        "Area",
        back_populates="tables",
        lazy="select",
    )
    orders: Mapped[list["Order"]] = relationship(  # noqa: F821
        "Order",
        back_populates="table",
        lazy="select",
    )

    # ------------------------------------------------------------------ #
    # Indexes & constraints                                                #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        UniqueConstraint("area_id", "table_number", name="uq_tables_area_table_number"),
        Index("ix_tables_is_active", "is_active"),
        Index("ix_tables_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Table id={self.id} number={self.table_number!r} status={self.status!r}>"
