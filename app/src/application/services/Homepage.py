import asyncio
import logging
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.core.Exceptions import NotFoundError
from src.models.OrderDetail import OrderDetail
from src.models.Workspace import Workspace
from src.models.Review import Review
from src.models.User import User
from src.repositories.HomepageRepository import HomepageRepository

logger = logging.getLogger(__name__)

# Order statuses that count as "processed"
_PROCESSED_STATUSES = ("completed", "paid")


class HomepageService(BaseService):
    """Service for homepage config CRUD and public data assembly."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.homepage_repo = HomepageRepository(db)
        super().__init__(self.homepage_repo)

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    async def get_config(self) -> Dict[str, Any]:
        """Return the singleton homepage config row."""
        config = await self.homepage_repo.get_config()
        if config is None:
            raise NotFoundError("Homepage config not found")
        return config

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
        """Build the 4 stat cards. Live counts run in parallel."""
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

    async def get_testimonials(self) -> List[Dict[str, Any]]:
        """Return top 5 most recent approved reviews as testimonials."""
        stmt = (
            select(
                Review.id,
                Review.rating,
                Review.comment,
                Review.created_at,
                User.first_name,
                User.last_name,
                Workspace.name.label("workspace_name"),
            )
            .outerjoin(User, Review.user_id == User.id)
            .join(Workspace, Review.workspace_id == Workspace.id)
            .where(
                Review.is_approved.is_(True),
                Review.is_active.is_(True),
                Workspace.is_active.is_(True),
            )
            .order_by(Review.created_at.desc())
            .limit(5)
        )
        rows = (await self.db.execute(stmt)).all()
        logger.debug("homepage.testimonials.fetched count=%s", len(rows))
        return [
            {
                "name": f"{row.first_name or ''} {row.last_name or ''}".strip() or "Anonymous",
                "role": "Customer",
                "rating": float(row.rating),
                "comment": row.comment or "",
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "workspace_name": row.workspace_name,
            }
            for row in rows
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
