"""
HomepageRepository — async SQLAlchemy 2.x repository for HomepageConfig.
Singleton pattern: always operates on the single row where singleton_key = 'default'.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Homepage import HomepageConfig


class HomepageRepository(BaseRepository):
    """Repository for the singleton HomepageConfig row."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(HomepageConfig, db)

    async def get_config(self) -> Optional[Dict[str, Any]]:
        """Fetch the singleton homepage config row."""
        stmt = select(HomepageConfig).where(
            HomepageConfig.singleton_key == "default",
            HomepageConfig.is_active.is_(True),
        )
        row = (await self.db.execute(stmt)).scalars().first()
        return row_to_dict(row) if row is not None else None

    async def update_config(self, data: Dict[str, Any]) -> bool:
        """
        Update the singleton row. Single round-trip UPDATE.
        Returns True if the row was found and updated.
        """
        payload = {**data, "updated_at": datetime.now(timezone.utc)}
        stmt = (
            update(HomepageConfig)
            .where(
                HomepageConfig.singleton_key == "default",
                HomepageConfig.is_active.is_(True),
            )
            .values(**payload)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0
