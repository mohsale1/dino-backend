"""
HomepageService — business logic for the public homepage.

Contact info and stat metadata come from the singleton homepage_config row.
Live counts (workspaces, orders processed) are always computed from the
actual tables — never stored.
"""

import asyncio
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.core.Exceptions import BadRequestError, NotFoundError
from src.models.OrderDetail import OrderDetail
from src.models.Workspace import Workspace
from src.repositories.HomepageRepository import HomepageRepository

# Order statuses that count as "processed"
_PROCESSED_STATUSES = ("completed", "paid")


class HomepageService(BaseService):
    """Service for homepage config CRUD and public data assembly."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.homepage_repo = HomepageRepository(db)
        super().__init__(self.homepage_repo)

    # ------------------------------------------------------------------
    # Config CRUD
    # ------------------------------------------------------------------

    async def get_config(self) -> Dict[str, Any]:
        """Return the singleton homepage config row.

        Raises
        ------
        NotFoundError
            If the config row has not been seeded yet.
        """
        config = await self.homepage_repo.get_config()
        if config is None:
            raise NotFoundError("Homepage config not found")
        return config

    async def update_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update the singleton config row and return the updated record.

        Raises
        ------
        BadRequestError
            If no fields are provided.
        NotFoundError
            If the config row does not exist.
        """
        if not data:
            raise BadRequestError("No fields provided to update")

        updated = await self.homepage_repo.update_config(data)
        if not updated:
            raise NotFoundError("Homepage config not found")

        return await self.get_config()

    # ------------------------------------------------------------------
    # Live count helpers
    # ------------------------------------------------------------------

    async def _count_workspaces(self) -> int:
        result = await self.db.execute(
            select(func.count(Workspace.id)).where(Workspace.is_active.is_(True))
        )
        return result.scalar_one() or 0

    async def _count_orders(self) -> int:
        result = await self.db.execute(
            select(func.count(OrderDetail.id)).where(
                OrderDetail.is_active.is_(True),
                OrderDetail.status.in_(_PROCESSED_STATUSES),
            )
        )
        return result.scalar_one() or 0

    # ------------------------------------------------------------------
    # Public data assembly
    # ------------------------------------------------------------------

    async def get_stats(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build the 4 stat cards. Live counts run in parallel.
        Metadata (labels, suffixes, icons) comes from the config row.
        """
        total_workspaces, total_orders = await asyncio.gather(
            self._count_workspaces(),
            self._count_orders(),
        )
        return [
            {
                "number": total_workspaces,
                "suffix": config.get("stat_businesses_suffix", "+"),
                "label": config.get("stat_businesses_label", "Active Businesses"),
                "icon": config.get("stat_businesses_icon", "business"),
            },
            {
                "number": total_orders,
                "suffix": config.get("stat_orders_suffix", "+"),
                "label": config.get("stat_orders_label", "Orders Processed"),
                "icon": config.get("stat_orders_icon", "shopping_cart"),
            },
            {
                "number": config.get("satisfaction", 98),
                "suffix": config.get("stat_satisfaction_suffix", "%"),
                "label": config.get("stat_satisfaction_label", "Customer Satisfaction"),
                "icon": config.get("stat_satisfaction_icon", "thumb_up"),
            },
            {
                "number": config.get("uptime", "99.9"),
                "suffix": config.get("stat_uptime_suffix", "%"),
                "label": config.get("stat_uptime_label", "Uptime"),
                "icon": config.get("stat_uptime_icon", "cloud_done"),
                "decimals": 1,
            },
        ]

    @staticmethod
    def get_contact(config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract contact fields from the config row."""
        return {
            "email": config.get("contact_email"),
            "phone": config.get("contact_phone"),
            "address": config.get("contact_address"),
            "city": config.get("contact_city"),
            "state": config.get("contact_state"),
            "postal_code": config.get("contact_postal_code"),
            "country": config.get("contact_country"),
        }
