"""
Venue Repository
Data access layer for venue collection
"""
from typing import List, Dict, Any, Optional

from app.repositories.base import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class VenueRepository(BaseRepository):
    """Repository for venue operations"""
    
    def __init__(self):
        super().__init__("venues")
    
    async def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get venues by workspace"""
        return await self.query([('workspace_id', '==', workspace_id)])
    
    async def get_by_owner(self, owner_id: str) -> List[Dict[str, Any]]:
        """Get venues owned by user"""
        return await self.query([('owner_id', '==', owner_id)])
    
    async def get_active_venues(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active venues, optionally filtered by workspace"""
        filters = [('is_active', '==', True)]
        if workspace_id:
            filters.append(('workspace_id', '==', workspace_id))
        return await self.query(filters)
    
    async def search_by_name(self, name: str, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search venues by name (case-insensitive partial match)"""
        # Note: Firestore doesn't support case-insensitive search natively
        # This is a simple implementation - for production, consider using Algolia or similar
        all_venues = await self.get_by_workspace(workspace_id) if workspace_id else await self.get_all()
        
        name_lower = name.lower()
        return [
            venue for venue in all_venues
            if name_lower in venue.get('name', '').lower()
        ]


# Singleton instance
_venue_repo = None

def get_venue_repository() -> VenueRepository:
    """Get venue repository singleton"""
    global _venue_repo
    if _venue_repo is None:
        _venue_repo = VenueRepository()
    return _venue_repo