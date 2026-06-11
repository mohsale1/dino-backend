"""
CustomerService — business logic for customers.
workspace_id and persona_id removed. mobile is globally unique.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseService import BaseService
from src.models.OrderDetail import OrderDetail
from src.repositories.CustomerRepository import CustomerRepository


class CustomerService(BaseService):
    """Service for managing customers."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.customer_repo = CustomerRepository(db)
        super().__init__(self.customer_repo)

    async def create_or_get_customer(
        self,
        name: str,
        mobile: str,
    ) -> Dict[str, Any]:
        """Upsert a customer by mobile. Returns existing or newly created."""
        existing = await self.customer_repo.get_by_mobile(mobile)
        if existing:
            return existing
        return await self.customer_repo.create({
            "name": name,
            "mobile": mobile,
            "is_active": True,
        })

    async def create_customer(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new customer record."""
        data.setdefault("is_active", True)
        return await self.customer_repo.create(data)

    async def get_paginated_customers(
        self,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated customers with optional search."""
        return await self.customer_repo.get_paginated(
            search=search,
            page=page,
            page_size=page_size,
        )

    async def get_customer_orders(
        self,
        customer_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated order_details for a customer."""
        conditions = [
            OrderDetail.customer_id == customer_id,
            OrderDetail.is_active.is_(True),
        ]
        where_expr = and_(*conditions)

        count_stmt = select(func.count()).select_from(OrderDetail).where(where_expr)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(OrderDetail)
            .where(where_expr)
            .order_by(OrderDetail.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages

    async def update_customer(self, customer_id: int, data: Dict[str, Any]) -> bool:
        return await self.customer_repo.update(customer_id, data)

    async def soft_delete_customer(self, customer_id: int) -> bool:
        return await self.customer_repo.soft_delete(customer_id)
