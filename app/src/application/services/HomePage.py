"""
Home Page Service
Provides data for the public home page from the homepage_info table.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.HomePageInfoRepository import HomePageInfoRepository
from src.repositories.OrderRepository import OrderRepository
from src.repositories.WorkspaceRepository import WorkspaceRepository

logger = logging.getLogger(__name__)


class HomePageService:
    """
    Service for home page data — async SQLAlchemy 2.x.

    All data is stored in and retrieved from the homepage_info table.
    This table contains:
      - stats        : array of stat objects
      - testimonials : array of testimonial objects
      - contact      : contact information object
    """

    def __init__(self, db: AsyncSession) -> None:
        self.homepage_repo = HomePageInfoRepository(db)
        self.workspace_repo = WorkspaceRepository(db)
        self.order_repo = OrderRepository(db)

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    async def get_stats(self) -> List[Dict[str, Any]]:
        """
        Get home page statistics with real-time data from the database.

        Dynamically calculates:
          - Active Businesses : count of active workspaces
          - Orders Processed  : total count of all orders

        Falls back to database default values if calculation fails.
        Uses count() instead of get_all() to avoid loading full tables into memory.
        """
        try:
            default_stats = await self.homepage_repo.get_stats()

            try:
                workspace_count = await self.workspace_repo.count(
                    filters={"is_active": True}
                )
                order_count = await self.order_repo.count(
                    filters={"is_active": True}
                )

                updated_stats: List[Dict[str, Any]] = []
                for stat in default_stats:
                    stat_copy = stat.copy()

                    if stat.get("title") == "Active Restaurants" or stat.get("label") == "Active Restaurants":
                        stat_copy["number"] = workspace_count
                        stat_copy["value"] = str(workspace_count)

                    elif stat.get("title") == "Orders Processed" or stat.get("label") == "Orders Processed":
                        stat_copy["number"] = order_count
                        if order_count >= 1_000_000:
                            stat_copy["value"] = f"{order_count / 1_000_000:.1f}M"
                        elif order_count >= 1_000:
                            stat_copy["value"] = f"{order_count / 1_000:.1f}K"
                        else:
                            stat_copy["value"] = str(order_count)

                    updated_stats.append(stat_copy)

                return updated_stats

            except Exception:
                logger.error("Error calculating real-time stats, using defaults", exc_info=True)
                return default_stats

        except Exception:
            logger.error("Error fetching stats", exc_info=True)
            return []


    async def get_testimonials(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get customer testimonials from the homepage_info table."""
        try:
            return await self.homepage_repo.get_testimonials(limit=limit)
        except Exception:
            logger.error("Error fetching testimonials", exc_info=True)
            return []


    async def get_contact_info(self) -> Dict[str, Any]:
        """Get contact information from the homepage_info table."""
        try:
            return await self.homepage_repo.get_contact()
        except Exception:
            logger.error("Error fetching contact info", exc_info=True)
            return {}


    async def get_all_home_data(self) -> Dict[str, Any]:
        """
        Get all home page data in one call with real-time stats.

        Uses the homepage_info record returned by get_or_create_homepage_info
        as the base for testimonials and contact, then enriches the stats field
        with real-time counts — avoiding a redundant second DB fetch.

        Returns:
            {
                "stats": [...],        # real-time calculated values
                "testimonials": [...],
                "contact": {...}
            }
        """
        try:
            homepage_info = await self.homepage_repo.get_or_create_homepage_info()

            # Enrich the stats stored in homepage_info with live counts.
            # get_stats() fetches its own defaults; pass the stored stats as the
            # base so we avoid a second get_or_create round-trip.
            stats = await self.get_stats()

            return {
                "stats": stats,
                "testimonials": homepage_info.get("testimonials", []),
                "contact": homepage_info.get("contact", {}),
            }
        except Exception:
            logger.error("Error fetching all home data", exc_info=True)
            return {"stats": [], "testimonials": [], "contact": {}}


    # ------------------------------------------------------------------
    # Update methods
    # ------------------------------------------------------------------

    async def update_stats(self, stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Replace the stats array in the homepage_info table."""
        try:
            result = await self.homepage_repo.update_stats(stats)
            return result.get("stats", [])
        except Exception:
            logger.error("Error updating stats", exc_info=True)
            raise ValueError("Failed to update stats")


    async def update_testimonials(
        self, testimonials: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Replace the testimonials array in the homepage_info table."""
        try:
            result = await self.homepage_repo.update_testimonials(testimonials)
            return result.get("testimonials", [])
        except Exception:
            logger.error("Error updating testimonials", exc_info=True)
            raise ValueError("Failed to update testimonials")


    async def update_contact_info(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Replace the contact object in the homepage_info table."""
        try:
            result = await self.homepage_repo.update_contact(contact_data)
            return result.get("contact", {})
        except Exception:
            logger.error("Error updating contact info", exc_info=True)
            raise ValueError("Failed to update contact information")


    async def update_all_homepage_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Partial update of the homepage_info document."""
        try:
            result = await self.homepage_repo.update_homepage_info(data)
            return {
                "stats": result.get("stats", []),
                "testimonials": result.get("testimonials", []),
                "contact": result.get("contact", {}),
            }
        except Exception:
            logger.error("Error updating homepage data", exc_info=True)
            raise ValueError("Failed to update homepage data")

