"""
Permission Repository
Handles all database operations for permissions
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.repositories.base import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class PermissionRepository(BaseRepository):
    """Repository for permission operations"""
    
    def __init__(self):
        super().__init__("permissions")
    
    async def create_permission(self, permission_data: Dict[str, Any]) -> str:
        """Create a new permission"""
        result = await super().create(permission_data)
        logger.info(f"Permission created: {permission_data.get('action')} ({result['id']})")
        return result['id']
    

    
    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get permission by name"""
        results = await self.query([("name", "==", name)], limit=1)
        return results[0] if results else None
    
    async def get_by_resource_and_action(self, resource: str, action: str) -> Optional[Dict[str, Any]]:
        """Get permission by resource and action combination"""
        name = f"{resource}.{action}"
        return await self.get_by_name(name)
    
    async def list_permissions(self, 
                              filters: Optional[Dict[str, Any]] = None,
                              page: int = 1,
                              page_size: int = 10) -> tuple[List[Dict[str, Any]], int]:
        """List permissions with pagination and filtering"""
        query = self.collection
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                if value is not None and field != 'search':
                    query = query.where(field, "==", value)
        
        # Get total count
        total_docs = list(query.stream())
        total = len(total_docs)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        docs = list(query.stream())
        permissions = [doc.to_dict() for doc in docs]
        
        # Apply search filter (client-side for Firestore)
        if filters and filters.get('search'):
            search_term = filters['search'].lower()
            permissions = [
                perm for perm in permissions
                if search_term in perm.get('name', '').lower() or
                   search_term in perm.get('description', '').lower() or
                   search_term in perm.get('resource', '').lower() or
                   search_term in perm.get('action', '').lower()
            ]
        
        return permissions, total
    
    async def update(self, permission_id: str, update_data: Dict[str, Any]) -> bool:
        """Update permission"""
        update_data['updated_at'] = datetime.utcnow()
        
        doc_ref = self.collection.document(permission_id)
        doc_ref.update(update_data)
        
        logger.info(f"Permission updated: {permission_id}")
        return True
    
    async def delete(self, permission_id: str) -> bool:
        """Delete permission (hard delete)"""
        self.collection.document(permission_id).delete()
        logger.info(f"Permission deleted: {permission_id}")
        return True
    
    async def get_roles_with_permission(self, permission_id: str) -> List[Dict[str, Any]]:
        """Get roles that have this permission"""
        roles_query = self.db.collection("roles").where("permission_ids", "array_contains", permission_id)
        roles_docs = list(roles_query.stream())
        return [doc.to_dict() for doc in roles_docs]
    
    async def get_permissions_by_category(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get permissions grouped by category"""
        query = self.collection
        if workspace_id:
            query = query.where("workspace_id", "==", workspace_id)
        
        docs = list(query.stream())
        permissions = [doc.to_dict() for doc in docs]
        
        # Group by resource
        categories = {}
        for perm in permissions:
            resource = perm.get('resource', 'uncategorized')
            if resource not in categories:
                categories[resource] = {
                    'name': resource,
                    'display_name': resource.replace('_', ' ').title(),
                    'description': f'Permissions related to {resource}',
                    'permissions': []
                }
            categories[resource]['permissions'].append(perm)
        
        return list(categories.values())
    
    async def get_permission_matrix(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Get permission matrix (resources vs actions)"""
        query = self.collection
        if workspace_id:
            query = query.where("workspace_id", "==", workspace_id)
        
        docs = list(query.stream())
        permissions = [doc.to_dict() for doc in docs]
        
        resources = set()
        actions = set()
        matrix = {}
        
        for perm in permissions:
            resource = perm.get('resource')
            action = perm.get('action')
            
            if resource and action:
                resources.add(resource)
                actions.add(action)
                
                if resource not in matrix:
                    matrix[resource] = {}
                matrix[resource][action] = perm
        
        return {
            'resources': sorted(list(resources)),
            'actions': sorted(list(actions)),
            'matrix': matrix
        }
    
    async def get_resources(self) -> List[str]:
        """Get all unique resources"""
        docs = list(self.collection.stream())
        resources = set()
        for doc in docs:
            data = doc.to_dict()
            if data.get('resource'):
                resources.add(data['resource'])
        return sorted(list(resources))
    
    async def get_actions(self) -> List[str]:
        """Get all unique actions"""
        docs = list(self.collection.stream())
        actions = set()
        for doc in docs:
            data = doc.to_dict()
            if data.get('action'):
                actions.add(data['action'])
        return sorted(list(actions))
    
    async def get_permission_statistics(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Get permission statistics"""
        query = self.collection
        if workspace_id:
            query = query.where("workspace_id", "==", workspace_id)
        
        docs = list(query.stream())
        permissions = [doc.to_dict() for doc in docs]
        
        stats = {
            "total_permissions": len(permissions),
            "permissions_by_resource": {},
            "permissions_by_action": {},
            "permissions_by_category": {},
            "unused_permissions": 0
        }
        
        # Count by resource, action, and scope
        for perm in permissions:
            resource = perm.get('resource', 'unknown')
            action = perm.get('action', 'unknown')
            scope = perm.get('scope', 'unknown')
            
            stats["permissions_by_resource"][resource] = stats["permissions_by_resource"].get(resource, 0) + 1
            stats["permissions_by_action"][action] = stats["permissions_by_action"].get(action, 0) + 1
            stats["permissions_by_category"][scope] = stats["permissions_by_category"].get(scope, 0) + 1
        
        # Count unused permissions
        for perm in permissions:
            roles = await self.get_roles_with_permission(perm['id'])
            if not roles:
                stats["unused_permissions"] += 1
        
        return stats
    
    async def bulk_create(self, permissions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk create permissions"""
        created = 0
        skipped = 0
        errors = []
        created_permissions = []
        
        for perm_data in permissions_data:
            try:
                # Check if permission with same name already exists
                existing = await self.get_by_name(perm_data['name'])
                if existing:
                    skipped += 1
                    errors.append(f"Permission '{perm_data['name']}' already exists")
                    continue
                
                # Create permission
                created_perm = await self.create(perm_data)
                created_permissions.append(created_perm)
                created += 1
                
            except Exception as e:
                skipped += 1
                errors.append(f"Failed to create permission '{perm_data.get('name', 'unknown')}': {str(e)}")
        
        return {
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "created_permissions": created_permissions
        }


# Singleton instance
_permission_repo = None

def get_permission_repository() -> PermissionRepository:
    """Get permission repository singleton"""
    global _permission_repo
    if _permission_repo is None:
        _permission_repo = PermissionRepository()
    return _permission_repo
