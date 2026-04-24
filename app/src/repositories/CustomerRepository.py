"""
CustomerRepository — async SQLAlchemy 2.x repository for the Customer model.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Customer import Customer


class CustomerRepository(BaseRepository):
    """Repository for Customer entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Customer, db)

    async def get_by_mobile_and_workspace(
        self, mobile: str, workspace_id: int
    ) -> Optional[Dict[str, Any]]:
        """Return the customer with the given mobile in the workspace."""
        stmt = (
            select(Customer)
            .where(
                Customer.mobile == mobile,
                Customer.workspace_id == workspace_id,
                Customer.is_active.is_(True),  # noqa: E712
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row else None

    async def get_by_workspace(
        self, workspace_id: int, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated customers for a workspace."""
        conditions = [Customer.workspace_id == workspace_id, Customer.is_active.is_(True)]  # noqa: E712

        count_stmt = select(func.count()).select_from(Customer).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(Customer)
            .where(and_(*conditions))
            .order_by(Customer.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages

    async def get_by_persona(self, persona_id: int) -> List[Dict[str, Any]]:
        """Return all active customers linked to a persona."""
        return await self.get_all(filters={"persona_id": persona_id})
