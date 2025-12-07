"""
Workspace Registration Service
Handles workspace setup and initial data creation
"""
from typing import Dict, Any
from datetime import datetime

from app.database.repository_manager import get_workspace_repo, get_venue_repo, get_user_repo, get_role_repo
from app.core.logging import get_logger
from app.core.security import get_password_hash
from app.utils.id_generator import generate_document_id

logger = get_logger(__name__)


class WorkspaceService:
    """Service for workspace registration and setup"""
    
    def __init__(self):
        self.workspace_repo = get_workspace_repo()
        self.venue_repo = get_venue_repo()
        self.user_repo = get_user_repo()
        self.role_repo = get_role_repo()
    
    async def register_workspace(self, registration_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new workspace with venue and admin user
        
        Args:
            registration_data: Registration information
        
        Returns:
            Created workspace, venue, and user information
        """
        # Generate IDs
        workspace_id = generate_document_id()
        venue_id = generate_document_id()
        user_id = generate_document_id()
        
        # 1. Create Workspace
        workspace_data = {
            "id": workspace_id,
            "name": registration_data.get('workspace_name'),
            "owner_id": user_id,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await self.workspace_repo.create(workspace_data)
        logger.info(f"Workspace created: {workspace_id}")
        
        # 2. Create Venue
        venue_data = {
            "id": venue_id,
            "workspace_id": workspace_id,
            "name": registration_data.get('venue_name'),
            "owner_id": user_id,
            "is_active": True,
            "is_verified": False,
            "rating": 0.0,
            "total_reviews": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Add optional venue fields
        if registration_data.get('venue_description'):
            venue_data['description'] = registration_data['venue_description']
        if registration_data.get('venue_phone'):
            venue_data['phone'] = registration_data['venue_phone']
        if registration_data.get('venue_email'):
            venue_data['email'] = registration_data['venue_email']
        
        await self.venue_repo.create(venue_data)
        logger.info(f"Venue created: {venue_id}")
        
        # 3. Get or create admin role
        admin_role = await self._get_or_create_admin_role()
        
        # 4. Create Admin User
        user_data = {
            "id": user_id,
            "workspace_id": workspace_id,
            "venue_id": venue_id,
            "email": registration_data.get('email'),
            "password_hash": get_password_hash(registration_data.get('password')),
            "first_name": registration_data.get('first_name'),
            "last_name": registration_data.get('last_name'),
            "role_id": admin_role['id'],
            "is_active": True,
            "is_verified": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await self.user_repo.create(user_data)
        logger.info(f"Admin user created: {user_id}")
        
        # 5. Update workspace with owner
        await self.workspace_repo.update(workspace_id, {"owner_id": user_id})
        
        return {
            "workspace": workspace_data,
            "venue": venue_data,
            "user": {
                "id": user_id,
                "email": user_data['email'],
                "first_name": user_data['first_name'],
                "last_name": user_data['last_name'],
                "role_id": admin_role['id']
            }
        }
    
    async def _get_or_create_admin_role(self) -> Dict[str, Any]:
        """Get or create admin role"""
        # Try to find existing admin role
        roles = await self.role_repo.query([('name', '==', 'admin')])
        
        if roles:
            return roles[0]
        
        # Create admin role if it doesn't exist
        admin_role_data = {
            "id": generate_document_id(),
            "name": "admin",
            "display_name": "Administrator",
            "description": "Full administrative access",
            "permission_ids": [],
            "is_system_role": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await self.role_repo.create(admin_role_data)
        logger.info(f"Admin role created: {admin_role_data['id']}")
        
        return admin_role_data


# Singleton instance
_workspace_service = None

def get_workspace_service() -> WorkspaceService:
    """Get workspace service singleton"""
    global _workspace_service
    if _workspace_service is None:
        _workspace_service = WorkspaceService()
    return _workspace_service