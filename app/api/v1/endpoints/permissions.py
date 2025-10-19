"""
Permissions Management API Endpoints
Comprehensive permission management with role mapping
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer
from datetime import datetime

from app.models.dto import (
    ApiResponseDTO as ApiResponse, PaginatedResponseDTO as PaginatedResponse,
    PermissionCreateDTO, PermissionUpdateDTO, PermissionResponseDTO, PermissionFiltersDTO,
    PermissionCategoryDTO, PermissionMatrixDTO, PermissionStatisticsDTO,
    BulkPermissionCreateDTO, BulkPermissionResponseDTO, NameAvailabilityDTO
)
from app.database.firestore import get_firestore_client
from app.core.security import get_current_user, get_current_admin_user
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()
security = HTTPBearer()

# Schemas are now imported from centralized locations

# =============================================================================
# PERMISSION REPOSITORY
# =============================================================================

class PermissionRepository:
    """Repository for permission operations"""
    
    def __init__(self):
        self.db = get_firestore_client()
        self.collection = "permissions"
    
    async def create(self, permission_data: Dict[str, Any]) -> str:
        """Create a new permission"""
        permission_data['created_at'] = datetime.utcnow()
        
        doc_ref = self.db.collection(self.collection).document()
        permission_data['id'] = doc_ref.id
        
        doc_ref.set(permission_data)  # Remove await - Firestore is synchronous
        logger.info(f"Permission created: {permission_data['action']} ({doc_ref.id})")
        return doc_ref.id
    
    async def get_by_id(self, permission_id: str) -> Optional[Dict[str, Any]]:
        """Get permission by ID"""
        doc = self.db.collection(self.collection).document(permission_id).get()  # Remove await
        if doc.exists:
            return doc.to_dict()
        return None
    
    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get permission by name"""
        query = self.db.collection(self.collection).where("name", "==", name)
        
        docs = list(query.limit(1).stream())  # Use stream() instead of get()
        if docs:
            return docs[0].to_dict()
        return None
    
    async def get_by_resource_and_action(self, resource: str, action: str) -> Optional[Dict[str, Any]]:
        """Get permission by resource and action combination"""
        name = f"{resource}.{action}"
        return await self.get_by_name(name)
    
    async def list_permissions(self, 
                              filters: Optional[Dict[str, Any]] = None,
                              page: int = 1,
                              page_size: int = 10) -> tuple[List[Dict[str, Any]], int]:
        """List permissions with pagination and filtering"""
        query = self.db.collection(self.collection)
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                if value is not None and field != 'search':
                    query = query.where(field, "==", value)
        
        # Get total count
        total_docs = list(query.stream())  # Use stream() instead of get()
        total = len(total_docs)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        docs = list(query.stream())  # Use stream() instead of get()
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
        
        doc_ref = self.db.collection(self.collection).document(permission_id)
        doc_ref.update(update_data)  # Remove await
        
        logger.info(f"Permission updated: {permission_id}")
        return True
    
    async def delete(self, permission_id: str) -> bool:
        """Delete permission (hard delete)"""
        self.db.collection(self.collection).document(permission_id).delete()  # Remove await
        logger.info(f"Permission deleted: {permission_id}")
        return True
    
    async def get_roles_with_permission(self, permission_id: str) -> List[Dict[str, Any]]:
        """Get roles that have this permission"""
        roles_query = self.db.collection("roles").where("permission_ids", "array_contains", permission_id)
        roles_docs = list(roles_query.stream())  # Use stream() instead of get()
        return [doc.to_dict() for doc in roles_docs]
    
    async def get_permissions_by_category(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get permissions grouped by category"""
        query = self.db.collection(self.collection)
        if workspace_id:
            query = query.where("workspace_id", "==", workspace_id)
        
        docs = list(query.stream())  # Use stream() instead of get()
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
        query = self.db.collection(self.collection)
        if workspace_id:
            query = query.where("workspace_id", "==", workspace_id)
        
        docs = list(query.stream())  # Use stream() instead of get()
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
        docs = list(self.db.collection(self.collection).stream())
        resources = set()
        for doc in docs:
            data = doc.to_dict()
            if data.get('resource'):
                resources.add(data['resource'])
        return sorted(list(resources))
    
    async def get_actions(self) -> List[str]:
        """Get all unique actions"""
        docs = list(self.db.collection(self.collection).stream())
        actions = set()
        for doc in docs:
            data = doc.to_dict()
            if data.get('action'):
                actions.add(data['action'])
        return sorted(list(actions))
    
    async def get_permission_statistics(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Get permission statistics"""
        query = self.db.collection(self.collection)
        if workspace_id:
            query = query.where("workspace_id", "==", workspace_id)
        
        docs = list(query.stream())  # Use stream() instead of get()
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
                perm_id = await self.create(perm_data)
                created_perm = await self.get_by_id(perm_id)
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

# Initialize repository
perm_repo = PermissionRepository()

# =============================================================================
# PERMISSION ENDPOINTS
# =============================================================================

@router.get("", 
            response_model=PaginatedResponse,
            summary="Get permissions",
            description="Get paginated list of permissions with filtering")
async def get_permissions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    name: Optional[str] = Query(None, description="Filter by name"),
    resource: Optional[str] = Query(None, description="Filter by resource"),
    action: Optional[str] = Query(None, description="Filter by action"),
    scope: Optional[str] = Query(None, description="Filter by scope"),
    search: Optional[str] = Query(None, description="Search by name, description, resource, or action")
):
    """Get permissions with pagination and filtering"""
    try:
        # Build filters
        filters = {}
        if name:
            filters['name'] = name
        if resource:
            filters['resource'] = resource
        if action:
            filters['action'] = action
        if scope:
            filters['scope'] = scope
        if search:
            filters['search'] = search
        
        permissions, total = await perm_repo.list_permissions(filters, page, page_size)
        
        # Enrich permissions with roles count
        enriched_permissions = []
        for perm in permissions:
            roles = await perm_repo.get_roles_with_permission(perm['id'])
            
            perm_response = PermissionResponseDTO(
                **perm,
                roles_count=len(roles)
            )
            enriched_permissions.append(perm_response.dict())
        
        total_pages = (total + page_size - 1) // page_size
        
        return PaginatedResponse(
            success=True,
            data=enriched_permissions,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
    except Exception as e:
        logger.error(f"Error getting permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permissions"
        )

@router.post("", 
             response_model=ApiResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Create permission",
             description="Create a new permission")
async def create_permission(
    permission_data: PermissionCreateDTO,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Create a new permission"""
    try:
        # Check if permission with same name already exists
        existing_permission = await perm_repo.get_by_name(permission_data.name)
        if existing_permission:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission with name '{permission_data.name}' already exists"
            )
        
        # Prepare permission data
        perm_dict = permission_data.dict()
        
        # Create permission
        perm_id = await perm_repo.create(perm_dict)
        
        # Get created permission
        created_permission = await perm_repo.get_by_id(perm_id)
        
        perm_response = PermissionResponseDTO(
            **created_permission,
            roles_count=0
        )
        
        logger.info(f"Permission created: {permission_data.name} by {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Permission created successfully",
            data=perm_response.dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create permission"
        )

@router.get("/{permission_id}", 
            response_model=PermissionResponseDTO,
            summary="Get permission by ID",
            description="Get specific permission by ID")
async def get_permission(
    permission_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get permission by ID"""
    try:
        permission = await perm_repo.get_by_id(permission_id)
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found"
            )
        
        # Access permissions removed for open API
        
        # Get roles count
        roles = await perm_repo.get_roles_with_permission(permission_id)
        
        perm_response = PermissionResponseDTO(
            **permission,
            roles_count=len(roles)
        )
        
        return perm_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permission"
        )

@router.put("/{permission_id}", 
            response_model=ApiResponse,
            summary="Update permission",
            description="Update permission information")
async def update_permission(
    permission_id: str,
    update_data: PermissionUpdateDTO,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Update permission"""
    try:
        # Check if permission exists
        permission = await perm_repo.get_by_id(permission_id)
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found"
            )
        
        # Get user role properly
        from app.core.security import _get_user_role
        user_role = await _get_user_role(current_user)
        
        # Only superadmin can update permissions
        if user_role != 'superadmin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmin can update permissions"
            )
        

        
        # Update permission
        update_dict = update_data.dict(exclude_unset=True)
        
        await perm_repo.update(permission_id, update_dict)
        
        # Get updated permission
        updated_permission = await perm_repo.get_by_id(permission_id)
        roles = await perm_repo.get_roles_with_permission(permission_id)
        
        perm_response = PermissionResponseDTO(
            **updated_permission,
            roles_count=len(roles)
        )
        
        logger.info(f"Permission updated: {permission_id} by {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Permission updated successfully",
            data=perm_response.dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update permission"
        )

@router.delete("/{permission_id}", 
               response_model=ApiResponse,
               summary="Delete permission",
               description="Delete permission (only if not assigned to any role)")
async def delete_permission(
    permission_id: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Delete permission"""
    try:
        # Check if permission exists
        permission = await perm_repo.get_by_id(permission_id)
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found"
            )
        
        # Get user role properly
        from app.core.security import _get_user_role
        user_role = await _get_user_role(current_user)
        
        # Only superadmin can delete permissions
        if user_role != 'superadmin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmin can delete permissions"
            )
        

        
        # Check if permission is assigned to any roles
        roles = await perm_repo.get_roles_with_permission(permission_id)
        if roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete permission. It is assigned to {len(roles)} roles"
            )
        
        # Delete permission
        await perm_repo.delete(permission_id)
        
        logger.info(f"Permission deleted: {permission_id} by {current_user['id']}")
        return ApiResponse(
            success=True,
            message="Permission deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete permission"
        )

# =============================================================================
# PERMISSION ORGANIZATION ENDPOINTS
# =============================================================================

@router.get("/by-category", 
            response_model=List[PermissionCategoryDTO],
            summary="Get permissions by category",
            description="Get permissions grouped by category")
async def get_permissions_by_category(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace")
):
    """Get permissions grouped by category"""
    try:
        # Workspace filtering removed for open API
        
        categories = await perm_repo.get_permissions_by_category(workspace_id)
        
        # Convert to response format
        category_responses = []
        for cat in categories:
            permissions = [
                PermissionResponseDTO(**perm, roles_count=0) 
                for perm in cat['permissions']
            ]
            category_responses.append(
                PermissionCategoryDTO(
                    name=cat['name'],
                    display_name=cat['display_name'],
                    description=cat['description'],
                    permissions=permissions
                )
            )
        
        return category_responses
        
    except Exception as e:
        logger.error(f"Error getting permissions by category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permissions by category"
        )

@router.get("/matrix", 
            response_model=PermissionMatrixDTO,
            summary="Get permission matrix",
            description="Get permission matrix (resources vs actions)")
async def get_permission_matrix(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace")
):
    """Get permission matrix"""
    try:
        # Workspace filtering removed for open API
        
        matrix_data = await perm_repo.get_permission_matrix(workspace_id)
        
        # Convert permissions to response format
        matrix = {}
        for resource, actions in matrix_data['matrix'].items():
            matrix[resource] = {}
            for action, perm in actions.items():
                if perm:
                    matrix[resource][action] = PermissionResponseDTO(**perm, roles_count=0)
                else:
                    matrix[resource][action] = None
        
        return PermissionMatrixDTO(
            resources=matrix_data['resources'],
            actions=matrix_data['actions'],
            matrix=matrix
        )
        
    except Exception as e:
        logger.error(f"Error getting permission matrix: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permission matrix"
        )

@router.get("/resources", 
            response_model=List[str],
            summary="Get available resources",
            description="Get all available resource names")
async def get_resources():
    """Get all available resources"""
    try:
        resources = await perm_repo.get_resources()
        return resources
        
    except Exception as e:
        logger.error(f"Error getting resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get resources"
        )

@router.get("/actions", 
            response_model=List[str],
            summary="Get available actions",
            description="Get all available action names")
async def get_actions():
    """Get all available actions"""
    try:
        actions = await perm_repo.get_actions()
        return actions
        
    except Exception as e:
        logger.error(f"Error getting actions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get actions"
        )

# =============================================================================
# BULK OPERATIONS
# =============================================================================

@router.post("/bulk-create", 
             response_model=BulkPermissionResponseDTO,
             summary="Bulk create permissions",
             description="Create multiple permissions at once")
async def bulk_create_permissions(
    bulk_data: BulkPermissionCreateDTO,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Bulk create permissions"""
    try:
        # Prepare permissions data
        permissions_data = []
        for perm in bulk_data.permissions:
            perm_dict = perm.dict()
            permissions_data.append(perm_dict)
        
        # Bulk create
        result = await perm_repo.bulk_create(permissions_data)
        
        # Convert created permissions to response format
        created_permissions = [
            PermissionResponseDTO(**perm, roles_count=0)
            for perm in result['created_permissions']
        ]
        
        logger.info(f"Bulk permission creation: {result['created']} created, {result['skipped']} skipped by {current_user['id']}")
        
        return BulkPermissionResponseDTO(
            success=True,
            created=result['created'],
            skipped=result['skipped'],
            errors=result['errors'],
            created_permissions=created_permissions
        )
        
    except Exception as e:
        logger.error(f"Error bulk creating permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk create permissions"
        )

# =============================================================================
# PERMISSION STATISTICS AND UTILITIES
# =============================================================================

@router.get("/statistics", 
            response_model=PermissionStatisticsDTO,
            summary="Get permission statistics",
            description="Get comprehensive permission statistics")
async def get_permission_statistics(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace")
):
    """Get permission statistics"""
    try:
        # Workspace filtering removed for open API
        
        stats = await perm_repo.get_permission_statistics(workspace_id)
        return PermissionStatisticsDTO(**stats)
        
    except Exception as e:
        logger.error(f"Error getting permission statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permission statistics"
        )

@router.get("/check-name", 
            response_model=Dict[str, bool],
            summary="Check permission name availability",
            description="Check if permission name is available")
async def check_permission_name_availability(
    name: str = Query(..., description="Permission name to check"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID"),
    exclude_id: Optional[str] = Query(None, description="Permission ID to exclude from check")
):
    """Check if permission name is available"""
    try:
        # Workspace filtering removed for open API
        
        existing_permission = await perm_repo.get_by_name(name)
        
        # If excluding a specific permission ID, check if it's the same permission
        if existing_permission and exclude_id and existing_permission.get('id') == exclude_id:
            return {"available": True}
        
        return {"available": existing_permission is None}
        
    except Exception as e:
        logger.error(f"Error checking permission name availability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check permission name availability"
        )

@router.get("/unused", 
            response_model=List[PermissionResponseDTO],
            summary="Get unused permissions",
            description="Get permissions not assigned to any role")
async def get_unused_permissions(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace")
):
    """Get unused permissions"""
    try:
        # Workspace filtering removed for open API
        
        # Get all permissions
        filters = {}
        if workspace_id:
            filters['workspace_id'] = workspace_id
        
        permissions, _ = await perm_repo.list_permissions(filters, 1, 1000)
        
        # Filter unused permissions
        unused_permissions = []
        for perm in permissions:
            roles = await perm_repo.get_roles_with_permission(perm['id'])
            if not roles:
                unused_permissions.append(
                    PermissionResponseDTO(**perm, roles_count=0)
                )
        
        return unused_permissions
        
    except Exception as e:
        logger.error(f"Error getting unused permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get unused permissions"
        )

# =============================================================================
# USER AND ROLE PERMISSION ENDPOINTS
# =============================================================================

@router.get("/users/{user_id}/permissions", 
            response_model=ApiResponse,
            summary="Get user permissions",
            description="Get all permissions assigned to a user (through their role)")
async def get_user_permissions(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all permissions for a specific user"""
    try:
        # Get user repository
        from app.database.firestore import get_user_repo
        user_repo = get_user_repo()
        
        # Get user
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Open access - no role restrictions for testing/development
        # Users can view any user's permissions (OPEN ACCESS)
        can_view_permissions = True
        
        # Optional: Log access for monitoring
        logger.info(f"User {current_user['id']} accessing permissions for user {user_id}")
        
        # Get user's role
        user_role_id = user.get('role_id')
        if not user_role_id:
            # If user has no role, return empty permissions with role info
            return ApiResponse(
                success=True,
                message="User permissions retrieved successfully",
                data={
                    "user_id": user_id,
                    "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                    "user_email": user.get('email'),
                    "role": None,
                    "permissions": [],
                    "total_permissions": 0
                }
            )
        
        # Get role repository
        from app.database.firestore import get_firestore_client
        db = get_firestore_client()
        
        # Get role
        role_doc = db.collection("roles").document(user_role_id).get()
        if not role_doc.exists:
            logger.warning(f"User {user_id} has invalid role_id: {user_role_id}")
            return ApiResponse(
                success=True,
                message="User permissions retrieved successfully",
                data={
                    "user_id": user_id,
                    "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                    "user_email": user.get('email'),
                    "role": {"id": user_role_id, "name": "Invalid Role", "exists": False},
                    "permissions": [],
                    "total_permissions": 0
                }
            )
        
        role_data = role_doc.to_dict()
        permission_ids = role_data.get('permission_ids', [])
        
        # Get permissions
        permissions = []
        for perm_id in permission_ids:
            permission = await perm_repo.get_by_id(perm_id)
            if permission:
                # Get roles count for this permission
                roles = await perm_repo.get_roles_with_permission(perm_id)
                perm_response = PermissionResponseDTO(
                    **permission,
                    roles_count=len(roles)
                )
                permissions.append(perm_response.dict())
        
        # Prepare response data
        response_data = {
            "user_id": user_id,
            "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "user_email": user.get('email'),
            "role": {
                "id": user_role_id,
                "name": role_data.get('name', 'Unknown'),
                "display_name": role_data.get('display_name', role_data.get('name', 'Unknown')),
                "description": role_data.get('description', ''),
                "exists": True
            },
            "permissions": permissions,
            "total_permissions": len(permissions)
        }
        
        logger.info(f"Retrieved {len(permissions)} permissions for user {user_id}")
        return ApiResponse(
            success=True,
            message="User permissions retrieved successfully",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user permissions"
        )

@router.get("/roles/{role_id}/permissions", 
            response_model=ApiResponse,
            summary="Get role permissions",
            description="Get all permissions assigned to a specific role")
async def get_role_permissions(
    role_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all permissions for a specific role"""
    try:
        # Open access - no role restrictions for testing/development
        # Any authenticated user can view role permissions (OPEN ACCESS)
        logger.info(f"User {current_user['id']} accessing permissions for role {role_id}")
        
        # Get role repository
        from app.database.firestore import get_firestore_client
        db = get_firestore_client()
        
        # Get role
        role_doc = db.collection("roles").document(role_id).get()
        if not role_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        role_data = role_doc.to_dict()
        permission_ids = role_data.get('permission_ids', [])
        
        # Get permissions
        permissions = []
        missing_permissions = []
        
        for perm_id in permission_ids:
            permission = await perm_repo.get_by_id(perm_id)
            if permission:
                # Get roles count for this permission
                roles = await perm_repo.get_roles_with_permission(perm_id)
                perm_response = PermissionResponseDTO(
                    **permission,
                    roles_count=len(roles)
                )
                permissions.append(perm_response.dict())
            else:
                missing_permissions.append(perm_id)
                logger.warning(f"Permission {perm_id} not found for role {role_id}")
        
        # Get users count for this role
        users_with_role = list(db.collection("users").where("role_id", "==", role_id).stream())
        users_count = len(users_with_role)
        
        # Prepare response data
        response_data = {
            "role_id": role_id,
            "role_name": role_data.get('name', 'Unknown'),
            "role_display_name": role_data.get('display_name', role_data.get('name', 'Unknown')),
            "role_description": role_data.get('description', ''),
            "permissions": permissions,
            "total_permissions": len(permissions),
            "users_with_role": users_count,
            "missing_permissions": missing_permissions if missing_permissions else None
        }
        
        logger.info(f"Retrieved {len(permissions)} permissions for role {role_id}")
        return ApiResponse(
            success=True,
            message="Role permissions retrieved successfully",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting role permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get role permissions"
        )

@router.get("/me/permissions", 
            response_model=List[PermissionResponseDTO],
            summary="Get current user permissions",
            description="Get all permissions for the currently authenticated user")
async def get_my_permissions(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get permissions for the current user"""
    return await get_user_permissions(current_user['id'], current_user)

@router.get("/users/{user_id}/permissions/detailed", 
            response_model=Dict[str, Any],
            summary="Get user permissions with role info",
            description="Get user permissions along with role information")
async def get_user_permissions_detailed(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get user permissions with detailed role information"""
    try:
        # Get user repository
        from app.database.firestore import get_user_repo
        user_repo = get_user_repo()
        
        # Get user
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check permissions
        if user_id != current_user['id']:
            from app.core.security import _get_user_role
            user_role = await _get_user_role(current_user)
            if user_role not in ['admin', 'superadmin']:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view this user's permissions"
                )
        
        # Get user's role
        user_role_id = user.get('role_id')
        if not user_role_id:
            return {
                "user_id": user_id,
                "role": None,
                "permissions": [],
                "total_permissions": 0
            }
        
        # Get role repository
        from app.database.firestore import get_firestore_client
        db = get_firestore_client()
        
        # Get role
        role_doc = db.collection("roles").document(user_role_id).get()
        if not role_doc.exists:
            return {
                "user_id": user_id,
                "role": {"id": user_role_id, "name": "Invalid Role", "exists": False},
                "permissions": [],
                "total_permissions": 0
            }
        
        role_data = role_doc.to_dict()
        permission_ids = role_data.get('permission_ids', [])
        
        # Get permissions
        permissions = []
        for perm_id in permission_ids:
            permission = await perm_repo.get_by_id(perm_id)
            if permission:
                roles = await perm_repo.get_roles_with_permission(perm_id)
                perm_response = PermissionResponseDTO(
                    **permission,
                    roles_count=len(roles)
                )
                permissions.append(perm_response.dict())
        
        return {
            "user_id": user_id,
            "role": {
                "id": user_role_id,
                "name": role_data.get('name', 'Unknown'),
                "display_name": role_data.get('display_name', role_data.get('name', 'Unknown')),
                "description": role_data.get('description', ''),
                "exists": True
            },
            "permissions": permissions,
            "total_permissions": len(permissions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting detailed user permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get detailed user permissions"
        )

@router.post("/users/{user_id}/permissions/check", 
             response_model=ApiResponse,
             summary="Check user permissions",
             description="Check if user has specific permissions")
async def check_user_permissions(
    user_id: str,
    permission_names: List[str],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Check if user has specific permissions"""
    try:
        # Open access - no role restrictions for testing/development
        # Any authenticated user can check any user's permissions (OPEN ACCESS)
        can_check_permissions = True
        
        logger.info(f"User {current_user['id']} checking permissions for user {user_id}")
        
        # Get user permissions (this returns ApiResponse now)
        user_perms_response = await get_user_permissions(user_id, current_user)
        user_permissions_data = user_perms_response.data
        user_permission_names = [perm['name'] for perm in user_permissions_data.get('permissions', [])]
        
        # Check each requested permission
        permission_check = {}
        for perm_name in permission_names:
            permission_check[perm_name] = perm_name in user_permission_names
        
        response_data = {
            "user_id": user_id,
            "user_name": user_permissions_data.get('user_name'),
            "role": user_permissions_data.get('role'),
            "requested_permissions": permission_names,
            "permission_results": permission_check,
            "has_all_permissions": all(permission_check.values()),
            "has_any_permissions": any(permission_check.values()),
            "missing_permissions": [perm for perm, has_perm in permission_check.items() if not has_perm]
        }
        
        return ApiResponse(
            success=True,
            message="Permission check completed successfully",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking user permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check user permissions"
        )

# =============================================================================
# SETUP ENDPOINTS (NO AUTHENTICATION)
# =============================================================================

@router.post("/setup/bulk-create", 
             response_model=BulkPermissionResponseDTO,
             summary="Setup: Bulk create permissions",
             description="Create multiple permissions at once (NO AUTH - SETUP ONLY)")
async def setup_bulk_create_permissions(
    bulk_data: BulkPermissionCreateDTO
    # NO AUTHENTICATION FOR SETUP
):
    """Bulk create permissions for system setup (NO AUTH)"""
    try:
        # Prepare permissions data for setup
        permissions_data = []
        for perm in bulk_data.permissions:
            perm_dict = perm.dict()
            permissions_data.append(perm_dict)
        
        # Bulk create
        result = await perm_repo.bulk_create(permissions_data)
        
        # Convert created permissions to response format
        created_permissions = [
            PermissionResponseDTO(**perm, roles_count=0)
            for perm in result['created_permissions']
        ]
        
        logger.info(f"Setup bulk permission creation: {result['created']} created, {result['skipped']} skipped")
        
        return BulkPermissionResponseDTO(
            success=True,
            created=result['created'],
            skipped=result['skipped'],
            errors=result['errors'],
            created_permissions=created_permissions
        )
        
    except Exception as e:
        logger.error(f"Error in setup bulk creating permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk create permissions: {str(e)}"
        )

@router.post("/setup/create", 
             response_model=ApiResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Setup: Create single permission",
             description="Create a single permission (NO AUTH - SETUP ONLY)")
async def setup_create_permission(
    permission_data: PermissionCreateDTO
    # NO AUTHENTICATION FOR SETUP
):
    """Create a single permission for system setup (NO AUTH)"""
    try:
        # Check if permission with same name already exists
        existing_permission = await perm_repo.get_by_name(permission_data.name)
        if existing_permission:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission with name '{permission_data.name}' already exists"
            )
        
        # Prepare permission data for setup
        perm_dict = permission_data.dict()
        
        # Create permission
        perm_id = await perm_repo.create(perm_dict)
        
        # Get created permission
        created_permission = await perm_repo.get_by_id(perm_id)
        
        perm_response = PermissionResponseDTO(
            **created_permission,
            roles_count=0
        )
        
        logger.info(f"Setup permission created: {permission_data.name}")
        return ApiResponse(
            success=True,
            message="Permission created successfully",
            data=perm_response.dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in setup creating permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create permission: {str(e)}"
        )

# =============================================================================
# ADDITIONAL PERMISSION UTILITY ENDPOINTS
# =============================================================================

@router.get("/users/{user_id}/permissions/summary", 
            response_model=ApiResponse,
            summary="Get user permissions summary",
            description="Get a summary of user permissions grouped by resource")
async def get_user_permissions_summary(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get user permissions summary grouped by resource"""
    try:
        # Check authorization (reuse logic from get_user_permissions)
        can_view_permissions = False
        
        # Open access - no role restrictions for testing/development
        can_view_permissions = True
        
        logger.info(f"User {current_user['id']} accessing permissions summary for user {user_id}")
        
        # Get user permissions
        user_perms_response = await get_user_permissions(user_id, current_user)
        user_permissions_data = user_perms_response.data
        permissions = user_permissions_data.get('permissions', [])
        
        # Group permissions by resource
        permissions_by_resource = {}
        for perm in permissions:
            resource = perm.get('resource', 'unknown')
            if resource not in permissions_by_resource:
                permissions_by_resource[resource] = {
                    'resource': resource,
                    'permissions': [],
                    'actions': []
                }
            permissions_by_resource[resource]['permissions'].append(perm)
            permissions_by_resource[resource]['actions'].append(perm.get('action', 'unknown'))
        
        # Convert to list and sort
        summary = list(permissions_by_resource.values())
        summary.sort(key=lambda x: x['resource'])
        
        response_data = {
            "user_id": user_id,
            "user_name": user_permissions_data.get('user_name'),
            "role": user_permissions_data.get('role'),
            "total_permissions": len(permissions),
            "resources_count": len(summary),
            "permissions_by_resource": summary
        }
        
        return ApiResponse(
            success=True,
            message="User permissions summary retrieved successfully",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user permissions summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user permissions summary"
        )

@router.get("/roles/{role_id}/permissions/summary", 
            response_model=ApiResponse,
            summary="Get role permissions summary",
            description="Get a summary of role permissions grouped by resource")
async def get_role_permissions_summary(
    role_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get role permissions summary grouped by resource"""
    try:
        # Open access - no role restrictions for testing/development
        # Any authenticated user can view role permissions summary (OPEN ACCESS)
        logger.info(f"User {current_user['id']} accessing permissions summary for role {role_id}")
        
        # Get role permissions
        role_perms_response = await get_role_permissions(role_id, current_user)
        role_permissions_data = role_perms_response.data
        permissions = role_permissions_data.get('permissions', [])
        
        # Group permissions by resource
        permissions_by_resource = {}
        for perm in permissions:
            resource = perm.get('resource', 'unknown')
            if resource not in permissions_by_resource:
                permissions_by_resource[resource] = {
                    'resource': resource,
                    'permissions': [],
                    'actions': []
                }
            permissions_by_resource[resource]['permissions'].append(perm)
            permissions_by_resource[resource]['actions'].append(perm.get('action', 'unknown'))
        
        # Convert to list and sort
        summary = list(permissions_by_resource.values())
        summary.sort(key=lambda x: x['resource'])
        
        response_data = {
            "role_id": role_id,
            "role_name": role_permissions_data.get('role_name'),
            "role_description": role_permissions_data.get('role_description'),
            "total_permissions": len(permissions),
            "resources_count": len(summary),
            "users_with_role": role_permissions_data.get('users_with_role'),
            "permissions_by_resource": summary
        }
        
        return ApiResponse(
            success=True,
            message="Role permissions summary retrieved successfully",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting role permissions summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get role permissions summary"
        )

@router.post("/validate-access", 
             response_model=ApiResponse,
             summary="Validate user access",
             description="Validate if a user has access to perform specific actions")
async def validate_user_access(
    user_id: str,
    resource: str,
    action: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Validate if user has access to perform a specific action on a resource"""
    try:
        # Open access - no role restrictions for testing/development
        # Any authenticated user can validate any user's access (OPEN ACCESS)
        can_validate_access = True
        
        logger.info(f"User {current_user['id']} validating access for user {user_id}")
        
        # Get user permissions
        user_perms_response = await get_user_permissions(user_id, current_user)
        user_permissions_data = user_perms_response.data
        permissions = user_permissions_data.get('permissions', [])
        
        # Check for specific permission
        permission_name = f"{resource}.{action}"
        has_permission = any(
            perm.get('name') == permission_name or 
            (perm.get('resource') == resource and perm.get('action') == action)
            for perm in permissions
        )
        
        # Also check for wildcard permissions
        wildcard_permissions = [
            f"{resource}.*",
            f"*.{action}",
            "*.*"
        ]
        
        has_wildcard = any(
            perm.get('name') in wildcard_permissions
            for perm in permissions
        )
        
        has_access = has_permission or has_wildcard
        
        response_data = {
            "user_id": user_id,
            "user_name": user_permissions_data.get('user_name'),
            "role": user_permissions_data.get('role'),
            "resource": resource,
            "action": action,
            "permission_name": permission_name,
            "has_access": has_access,
            "access_type": "direct" if has_permission else ("wildcard" if has_wildcard else "none"),
            "matching_permissions": [
                perm for perm in permissions 
                if perm.get('name') == permission_name or 
                   (perm.get('resource') == resource and perm.get('action') == action) or
                   perm.get('name') in wildcard_permissions
            ]
        }
        
        return ApiResponse(
            success=True,
            message="Access validation completed successfully",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating user access: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate user access"
        )