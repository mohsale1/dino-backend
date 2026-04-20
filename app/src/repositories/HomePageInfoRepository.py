"""
HomePageInfoRepository — dino-application.

Manages the single-row homepage_info table (id always = 1).
No soft-delete columns exist on this model; updates are always in-place.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.HomePageInfo import HomePageInfo

_DEFAULT_STATS: List[Dict[str, Any]] = [
    {
        "title": "Active Restaurants",
        "value": "1",
        "number": 1,
        "suffix": "+",
        "label": "Active Restaurants",
        "icon": "restaurant",
    },
    {
        "title": "Orders Processed",
        "value": "0",
        "number": 0,
        "suffix": "+",
        "label": "Orders Processed",
        "icon": "shopping_cart",
    },
    {
        "title": "Happy Customers",
        "value": "0",
        "number": 0,
        "suffix": "+",
        "label": "Happy Customers",
        "icon": "people",
    },
    {
        "title": "Menu Items",
        "value": "0",
        "number": 0,
        "suffix": "+",
        "label": "Menu Items",
        "icon": "menu_book",
    },
]

_DEFAULT_TESTIMONIALS: List[Dict[str, Any]] = [
    {
        "name": "Rajesh Kumar",
        "role": "Owner",
        "restaurant": "Spice Garden Restaurant",
        "location": "Mumbai, Maharashtra",
        "rating": 5,
        "comment": (
            "Dino transformed our restaurant operations completely. Orders are faster, "
            "more accurate, and our customers love the digital menu experience. Highly recommended!"
        ),
        "avatar": "RK",
    },
    {
        "name": "Priya Sharma",
        "role": "Manager",
        "restaurant": "Cafe Coffee Day",
        "location": "Bangalore, Karnataka",
        "rating": 5,
        "comment": (
            "The analytics dashboard gives us incredible insights into our business. "
            "We've increased our revenue by 30% since implementing Dino. Best decision ever!"
        ),
        "avatar": "PS",
    },
    {
        "name": "Amit Patel",
        "role": "Owner",
        "restaurant": "Gujarat Bhavan",
        "location": "Ahmedabad, Gujarat",
        "rating": 5,
        "comment": (
            "Managing multiple outlets was a challenge until we found Dino. "
            "Now everything is centralized and efficient. Our staff loves how easy it is to use."
        ),
        "avatar": "AP",
    },
    {
        "name": "Sneha Reddy",
        "role": "Co-founder",
        "restaurant": "South Indian Delights",
        "location": "Hyderabad, Telangana",
        "rating": 5,
        "comment": (
            "The QR code ordering system is a game-changer! Our customers can browse the menu "
            "and place orders seamlessly. Customer satisfaction has gone up significantly."
        ),
        "avatar": "SR",
    },
    {
        "name": "Vikram Singh",
        "role": "Owner",
        "restaurant": "Punjabi Tadka",
        "location": "Chandigarh, Punjab",
        "rating": 5,
        "comment": (
            "Dino helped us go digital without any hassle. The support team is amazing and the "
            "platform is very user-friendly. Our business has grown 40% in just 6 months!"
        ),
        "avatar": "VS",
    },
    {
        "name": "Meera Iyer",
        "role": "Manager",
        "restaurant": "Saravana Bhavan",
        "location": "Chennai, Tamil Nadu",
        "rating": 5,
        "comment": (
            "Real-time order tracking and inventory management features are outstanding. "
            "We can now serve more customers efficiently and reduce wastage significantly."
        ),
        "avatar": "MI",
    },
]

_DEFAULT_CONTACT: Dict[str, Any] = {
    "email": "contact@dino.restaurant",
    "phone": "+1 (555) 123-4567",
    "address": "123 Restaurant Street",
    "city": "San Francisco",
    "state": "CA",
    "country": "United States",
    "postal_code": "94102",
}


class HomePageInfoRepository(BaseRepository):
    """Repository for the singleton homepage_info row (id = 1)."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(HomePageInfo, db)

    # ------------------------------------------------------------------
    # Core read
    # ------------------------------------------------------------------

    async def get_homepage_info(self) -> Optional[dict]:
        """Return the singleton row as a dict, or None if it does not exist yet."""
        stmt = select(HomePageInfo).where(HomePageInfo.id == 1)
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row else None

    async def get_or_create_homepage_info(self) -> dict:
        """Return the singleton row, creating it with defaults if absent.

        Uses INSERT ... ON CONFLICT (id) DO NOTHING so concurrent requests
        never race to insert a duplicate row.  The row is always fetched
        after the upsert to return the authoritative persisted state.
        """
        stmt = (
            pg_insert(HomePageInfo)
            .values(
                id=1,
                stats=_DEFAULT_STATS,
                testimonials=_DEFAULT_TESTIMONIALS,
                contact=_DEFAULT_CONTACT,
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await self.db.execute(stmt)
        return await self.get_homepage_info()


    # ------------------------------------------------------------------
    # Core write
    # ------------------------------------------------------------------

    async def update_homepage_info(self, data: Dict[str, Any]) -> dict:
        """
        Partial update of the singleton row.
        Creates the row with defaults first if it does not exist, then applies *data*.
        """
        existing = await self.get_homepage_info()

        if existing:
            stmt = (
                update(HomePageInfo)
                .where(HomePageInfo.id == 1)
                .values(**data)
                .execution_options(synchronize_session="fetch")
            )
            await self.db.execute(stmt)
        else:
            # Merge defaults with the supplied partial data
            instance = HomePageInfo(
                id=1,
                stats=data.get("stats", _DEFAULT_STATS),
                testimonials=data.get("testimonials", _DEFAULT_TESTIMONIALS),
                contact=data.get("contact", _DEFAULT_CONTACT),
            )
            self.db.add(instance)
            await self.db.flush()

        # Re-fetch to return the current persisted state
        return await self.get_homepage_info()

    # ------------------------------------------------------------------
    # Convenience section writers
    # ------------------------------------------------------------------

    async def update_stats(self, stats: List[Dict[str, Any]]) -> dict:
        """Replace the stats array."""
        return await self.update_homepage_info({"stats": stats})

    async def update_testimonials(self, testimonials: List[Dict[str, Any]]) -> dict:
        """Replace the testimonials array."""
        return await self.update_homepage_info({"testimonials": testimonials})

    async def update_contact(self, contact: Dict[str, Any]) -> dict:
        """Replace the contact object."""
        return await self.update_homepage_info({"contact": contact})

    # ------------------------------------------------------------------
    # Convenience section readers
    # ------------------------------------------------------------------

    async def get_stats(self) -> List[Dict[str, Any]]:
        """Return the stats array, creating the row if needed."""
        info = await self.get_or_create_homepage_info()
        return info.get("stats") or []

    async def get_testimonials(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return testimonials, optionally capped to *limit* entries."""
        info = await self.get_or_create_homepage_info()
        testimonials: list = info.get("testimonials") or []
        return testimonials[:limit] if limit else testimonials

    async def get_contact(self) -> Dict[str, Any]:
        """Return the contact object, creating the row if needed."""
        info = await self.get_or_create_homepage_info()
        return info.get("contact") or {}
