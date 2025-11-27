"""
Workspace Repository
Data access layer for workspace collection
"""
from typing import List, Dict, Any, Optional

from app.repositories.base import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkspaceRepository(BaseRepository):
    """Repository for workspace operations"""
    
    def __init__(self):
        super().__init__("workspaces")
    
    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get workspace by name"""
        results = await self.query([('name', '==', name)])
        return results[0] if results else None
    
    async def get_active_workspaces(self) -> List[Dict[str, Any]]:
        """Get all active workspaces"""
        return await self.query([('is_active', '==', True)])
    
    async def get_by_owner(self, owner_id: str) -> List[Dict[str, Any]]:
        """Get workspaces owned by user"""
        return await self.query([('owner_id', '==', owner_id)])
    
    async def add_venue_to_workspace(self, workspace_id: str, venue_id: str) -> bool:
        """Add venue to workspace"""
        try:
            workspace = await self.get_by_id(workspace_id)
            if not workspace:
                return False
            
            venue_ids = workspace.get('venue_ids', [])
            if venue_id not in venue_ids:
                venue_ids.append(venue_id)
                await self.update(workspace_id, {'venue_ids': venue_ids})
            
            return True
        except Exception as e:
            logger.error(f"Error adding venue to workspace: {e}")
            raise
    
    async def remove_venue_from_workspace(self, workspace_id: str, venue_id: str) -> bool:
        """Remove venue from workspace"""
        try:
            workspace = await self.get_by_id(workspace_id)
            if not workspace:
                return False
            
            venue_ids = workspace.get('venue_ids', [])
            if venue_id in venue_ids:
                venue_ids.remove(venue_id)
                await self.update(workspace_id, {'venue_ids': venue_ids})
            
            return True
        except Exception as e:
            logger.error(f"Error removing venue from workspace: {e}")
            raise


# Singleton instance
_workspace_repo = None

def get_workspace_repository() -> WorkspaceRepository:
    """Get workspace repository singleton"""
    global _workspace_repo
    if _workspace_repo is None:
        _workspace_repo = WorkspaceRepository()
    return _workspace_repo