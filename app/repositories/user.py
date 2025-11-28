"""
User Repository
Data access layer for user collection
"""
from typing import List, Dict, Any, Optional

from app.repositories.base import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class UserRepository(BaseRepository):
    """Repository for user operations"""
    
    def __init__(self):
        super().__init__("users")
    
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        results = await self.query([('email', '==', email)])
        return results[0] if results else None
    
    async def get_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get user by phone"""
        results = await self.query([('phone', '==', phone)])
        return results[0] if results else None
    
    async def get_by_role(self, role_id: str) -> List[Dict[str, Any]]:
        """Get users by role"""
        return await self.query([('role_id', '==', role_id)])
    
    async def get_by_venue(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get users assigned to a venue"""
        return await self.query([('venue_ids', 'array_contains', venue_id)])
    
    async def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get users in a workspace"""
        return await self.query([('workspace_id', '==', workspace_id)])
    
    async def get_active_users(self) -> List[Dict[str, Any]]:
        """Get all active users"""
        return await self.query([('is_active', '==', True)])
    
    async def assign_to_venue(self, user_id: str, venue_id: str) -> bool:
        """Assign user to a venue"""
        try:
            user = await self.get_by_id(user_id)
            if not user:
                return False
            
            venue_ids = user.get('venue_ids', [])
            if venue_id not in venue_ids:
                venue_ids.append(venue_id)
                await self.update(user_id, {'venue_ids': venue_ids})
            
            return True
        except Exception as e:
            logger.error(f"Error assigning user to venue: {e}")
            raise
    
    async def remove_from_venue(self, user_id: str, venue_id: str) -> bool:
        """Remove user from a venue"""
        try:
            user = await self.get_by_id(user_id)
            if not user:
                return False
            
            venue_ids = user.get('venue_ids', [])
            if venue_id in venue_ids:
                venue_ids.remove(venue_id)
                await self.update(user_id, {'venue_ids': venue_ids})
            
            return True
        except Exception as e:
            logger.error(f"Error removing user from venue: {e}")
            raise


# Singleton instance
_user_repo = None

def get_user_repository() -> UserRepository:
    """Get user repository singleton"""
    global _user_repo
    if _user_repo is None:
        _user_repo = UserRepository()
    return _user_repo