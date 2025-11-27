"""
User Service
Business logic for user management
"""
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.database.repository_manager import get_user_repo
from app.core.logging import get_logger
from app.core.security import get_password_hash, verify_password

logger = get_logger(__name__)


class UserService:
    """Service for user business logic"""
    
    def __init__(self):
        self.repo = get_user_repo()
    
    async def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """Update user profile information"""
        update_data = {}
        
        # Only update allowed profile fields
        allowed_fields = ['first_name', 'last_name', 'phone', 'avatar_url', 'bio']
        for field in allowed_fields:
            if field in profile_data:
                update_data[field] = profile_data[field]
        
        if update_data:
            update_data['updated_at'] = datetime.utcnow()
            await self.repo.update(user_id, update_data)
            logger.info(f"User profile updated: {user_id}")
            return True
        
        return False
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences"""
        await self.repo.update(user_id, {
            "preferences": preferences,
            "updated_at": datetime.utcnow()
        })
        
        logger.info(f"User preferences updated: {user_id}")
        return True
    
    async def update_user_address(self, user_id: str, address: Dict[str, Any]) -> bool:
        """Update user address"""
        await self.repo.update(user_id, {
            "address": address,
            "updated_at": datetime.utcnow()
        })
        
        logger.info(f"User address updated: {user_id}")
        return True
    
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password"""
        user = await self.repo.get_by_id(user_id)
        if not user:
            return False
        
        # Verify current password
        if not verify_password(current_password, user.get('password_hash', '')):
            return False
        
        # Update password
        new_password_hash = get_password_hash(new_password)
        await self.repo.update(user_id, {
            "password_hash": new_password_hash,
            "password_changed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        logger.info(f"Password changed for user: {user_id}")
        return True
    
    async def activate_user(self, user_id: str) -> bool:
        """Activate user account"""
        await self.repo.update(user_id, {
            "is_active": True,
            "activated_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        logger.info(f"User activated: {user_id}")
        return True
    
    async def deactivate_user(self, user_id: str, reason: Optional[str] = None) -> bool:
        """Deactivate user account"""
        update_data = {
            "is_active": False,
            "deactivated_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        if reason:
            update_data['deactivation_reason'] = reason
        
        await self.repo.update(user_id, update_data)
        
        logger.info(f"User deactivated: {user_id}")
        return True
    
    async def verify_user_email(self, user_id: str) -> bool:
        """Verify user email"""
        await self.repo.update(user_id, {
            "is_verified": True,
            "email_verified_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        logger.info(f"User email verified: {user_id}")
        return True
    
    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        await self.repo.update(user_id, {
            "last_login": datetime.utcnow()
        })
        
        return True
    
    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics"""
        user = await self.repo.get_by_id(user_id)
        if not user:
            return None
        
        # Get related data counts
        from app.database.repository_manager import get_order_repo
        order_repo = get_order_repo()
        
        # Count user's orders
        user_orders = await order_repo.query([('customer_id', '==', user_id)])
        
        return {
            "user_id": user_id,
            "total_orders": len(user_orders),
            "account_created": user.get('created_at'),
            "last_login": user.get('last_login'),
            "is_active": user.get('is_active', False),
            "is_verified": user.get('is_verified', False)
        }
    
    async def search_users(self, search_term: str, workspace_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Search users by name or email"""
        # Get all users (or by workspace)
        if workspace_id:
            users = await self.repo.query([('workspace_id', '==', workspace_id)])
        else:
            users = await self.repo.get_all()
        
        # Filter by search term
        search_lower = search_term.lower()
        matching_users = []
        
        for user in users:
            if (search_lower in user.get('email', '').lower() or
                search_lower in user.get('first_name', '').lower() or
                search_lower in user.get('last_name', '').lower()):
                matching_users.append(user)
                
                if len(matching_users) >= limit:
                    break
        
        return matching_users


# Singleton instance
_user_service = None

def get_user_service() -> UserService:
    """Get user service singleton"""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service