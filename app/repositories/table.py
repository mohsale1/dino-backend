"""
Table Repository
Data access layer for tables and table areas
"""
from typing import List, Dict, Any, Optional

from app.repositories.base import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class TableAreaRepository(BaseRepository):
    """Repository for table area operations"""
    
    def __init__(self):
        super().__init__("table_areas")
    
    async def get_by_venue(self, venue_id: str, active_only: bool = False) -> List[Dict[str, Any]]:
        """Get table areas by venue"""
        filters = [('venue_id', '==', venue_id)]
        if active_only:
            filters.append(('is_active', '==', True))
        return await self.query(filters)
    
    async def get_by_name(self, venue_id: str, name: str) -> Optional[Dict[str, Any]]:
        """Get table area by name within a venue"""
        results = await self.query([
            ('venue_id', '==', venue_id),
            ('name', '==', name)
        ])
        return results[0] if results else None


class TableRepository(BaseRepository):
    """Repository for table operations"""
    
    def __init__(self):
        super().__init__("tables")
    
    async def get_by_venue(self, venue_id: str, active_only: bool = False) -> List[Dict[str, Any]]:
        """Get tables by venue"""
        filters = [('venue_id', '==', venue_id)]
        if active_only:
            filters.append(('is_active', '==', True))
        return await self.query(filters)
    
    async def get_by_area(self, area_id: str) -> List[Dict[str, Any]]:
        """Get tables by area"""
        return await self.query([('area_id', '==', area_id)])
    
    async def get_by_status(self, venue_id: str, status: str) -> List[Dict[str, Any]]:
        """Get tables by status"""
        return await self.query([
            ('venue_id', '==', venue_id),
            ('table_status', '==', status)
        ])
    
    async def get_by_table_number(self, venue_id: str, table_number: str) -> Optional[Dict[str, Any]]:
        """Get table by number within a venue"""
        results = await self.query([
            ('venue_id', '==', venue_id),
            ('table_number', '==', table_number)
        ])
        return results[0] if results else None
    
    async def get_available_tables(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get available tables"""
        return await self.query([
            ('venue_id', '==', venue_id),
            ('table_status', '==', 'available'),
            ('is_active', '==', True)
        ])
    
    async def update_status(self, table_id: str, status: str) -> bool:
        """Update table status"""
        try:
            await self.update(table_id, {'table_status': status})
            return True
        except Exception as e:
            logger.error(f"Error updating table status: {e}")
            raise


# Singleton instances
_area_repo = None
_table_repo = None

def get_table_area_repository() -> TableAreaRepository:
    """Get table area repository singleton"""
    global _area_repo
    if _area_repo is None:
        _area_repo = TableAreaRepository()
    return _area_repo

def get_table_repository() -> TableRepository:
    """Get table repository singleton"""
    global _table_repo
    if _table_repo is None:
        _table_repo = TableRepository()
    return _table_repo