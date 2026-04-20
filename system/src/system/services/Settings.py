from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.HomePageInfoRepository import HomePageInfoRepository


class SettingsService:
    """Service for managing system-wide settings."""

    def __init__(self, db: AsyncSession) -> None:
        self.homepage_repo = HomePageInfoRepository(db)

    async def get_homepage_info(self) -> Dict[str, Any]:
        """Return the singleton homepage info row, creating it with defaults if absent."""
        return await self.homepage_repo.get_or_create_homepage_info()

    async def update_homepage_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Partial update of the homepage info row.

        The underlying table stores three JSONB columns: stats, testimonials, contact.
        Only keys present in *data* are forwarded to the repository; unrecognised keys
        are silently ignored so callers can pass the full request payload safely.
        """
        update_data: Dict[str, Any] = {}

        if "stats" in data:
            raw = data["stats"]
            # Accept either a plain list or {"items": [...]} envelope
            update_data["stats"] = raw.get("items", raw) if isinstance(raw, dict) else raw

        if "testimonials" in data:
            raw = data["testimonials"]
            update_data["testimonials"] = raw.get("items", raw) if isinstance(raw, dict) else raw

        if "contact" in data:
            update_data["contact"] = data["contact"]

        return await self.homepage_repo.update_homepage_info(update_data)
