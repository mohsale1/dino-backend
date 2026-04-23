"""
CustomerService — business logic for customers.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseService import BaseService
from src.models.Customer import Customer
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
        workspace_id: int,
        persona_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Upsert a customer by mobile + workspace_id. Returns existing or newly created."""
        existing = await self.customer_repo.get_by_mobile_and_workspace(mobile, workspace_id)
        if existing:
            return existing
        payload: Dict[str, Any] = {
            "name": name,
            "mobile": mobile,
            "workspace_id": workspace_id,
            "is_active": True,
        }
        if persona_id is not None:
            payload["persona_id"] = persona_id
        return await self.customer_repo.create(payload)

    async def create_customer(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new customer record."""
        data.setdefault("is_active", True)
        return await self.customer_repo.create(data)

    async def get_paginated_customers(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated customers with optional search."""
        conditions = [
            Customer.workspace_id == workspace_id,
            Customer.is_active == True,  # noqa: E712
        ]
        if persona_id is not None:
            conditions.append(Customer.persona_id == persona_id)
        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(
                    Customer.name.ilike(pattern),
                    Customer.mobile.ilike(pattern),
                )
            )

        where_expr = and_(*conditions)
        count_stmt = select(func.count()).select_from(Customer).where(where_expr)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(Customer)
            .where(where_expr)
            .order_by(Customer.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages

    async def get_customer_orders(
        self,
        customer_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated order_details for a customer."""
        conditions = [
            OrderDetail.customer_id == customer_id,
            OrderDetail.is_active == True,  # noqa: E712
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
