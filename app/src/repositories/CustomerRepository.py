from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseRepository import BaseRepository
from src.models.Customer import Customer
from src.models.Order import Order
from src.base.BaseModel import row_to_dict


class CustomerRepository(BaseRepository):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Customer, db)

    async def get_by_mobile_and_workspace(
        self,
        mobile: str,
        workspace_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Look up an active customer by mobile number within a workspace."""
        stmt = (
            select(Customer)
            .where(
                and_(
                    Customer.mobile == mobile,
                    Customer.workspace_id == workspace_id,
                    Customer.is_active == True,  # noqa: E712
                )
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row is not None else None

    async def get_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        """Return all active customers belonging to a workspace."""
        return await self.get_all(
            filters={"workspace_id": workspace_id},
            order_by="created_at",
            order_direction="desc",
        )

    async def get_order_history(self, customer_id: int) -> List[Dict[str, Any]]:
        """Return all active orders linked to a customer, newest first."""
        stmt = (
            select(Order)
            .where(
                and_(
                    Order.customer_id == customer_id,
                    Order.is_active == True,  # noqa: E712
                )
            )
            .order_by(Order.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return [row_to_dict(row) for row in result.scalars().all()]
