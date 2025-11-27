"""
Permissions Management API Endpoints
Comprehensive permission management with role mapping
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer

from app.models.requests import (
    ApiResponseDTO as ApiResponse, PaginatedResponseDTO as PaginatedResponse,
    PermissionCreateDTO, PermissionUpdateDTO, PermissionResponseDTO, PermissionFiltersDTO,
    PermissionCategoryDTO, PermissionMatrixDTO, PermissionStatisticsDTO,
    BulkPermissionCreateDTO, BulkPermissionResponseDTO, NameAvailabilityDTO
)
from app.repositories.permission import PermissionRepository
from app.services.permission import get_permission_service
from app.core.security import get_current_user, get_current_admin_user, _get_user_role
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()
security = HTTPBearer()

# Initialize repository and service
perm_repo = PermissionRepository()
perm_service = get_permission_service()


# =============================================================================
# CORE PERMISSION CRUD ENDPOINTS
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
            perm_response = PermissionResponseDTO(**perm, roles_count=len(roles))
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
        
        # Create permission
        perm_dict = permission_data.dict()
        perm_id = await perm_repo.create(perm_dict)
        
        # Get created permission
        created_permission = await perm_repo.get_by_id(perm_id)
        perm_response = PermissionResponseDTO(**created_permission, roles_count=0)
        
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
        
        # Get roles count
        roles = await perm_repo.get_roles_with_permission(permission_id)
        perm_response = PermissionResponseDTO(**permission, roles_count=len(roles))
        
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
        
        # Only superadmin can update permissions
        user_role = await _get_user_role(current_user)
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
        perm_response = PermissionResponseDTO(**updated_permission, roles_count=len(roles))
        
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
        
        # Only superadmin can delete permissions
        user_role = await _get_user_role(current_user)
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
        permissions_data = [perm.dict() for perm in bulk_data.permissions]
        result = await perm_repo.bulk_create(permissions_data)
        
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
# STATISTICS AND UTILITIES
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
        existing_permission = await perm_repo.get_by_name(name)
        
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
        filters = {}
        if workspace_id:
            filters['workspace_id'] = workspace_id
        
        permissions, _ = await perm_repo.list_permissions(filters, 1, 1000)
        
        # Filter unused permissions
        unused_permissions = []
        for perm in permissions:
            roles = await perm_repo.get_roles_with_permission(perm['id'])
            if not roles:
                unused_permissions.append(PermissionResponseDTO(**perm, roles_count=0))
        
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
        logger.info(f"User {current_user['id']} accessing permissions for user {user_id}")
        
        response_data = await perm_service.get_user_permissions(user_id)
        
        logger.info(f"Retrieved {response_data['total_permissions']} permissions for user {user_id}")
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
        logger.info(f"User {current_user['id']} accessing permissions for role {role_id}")
        
        response_data = await perm_service.get_role_permissions(role_id)
        if not response_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        logger.info(f"Retrieved {response_data['total_permissions']} permissions for role {role_id}")
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
        logger.info(f"User {current_user['id']} checking permissions for user {user_id}")
        
        response_data = await perm_service.check_user_permissions(user_id, permission_names)
        
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
        logger.info(f"User {current_user['id']} accessing permissions summary for user {user_id}")
        
        response_data = await perm_service.get_permissions_summary(user_id)
        
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
        logger.info(f"User {current_user['id']} accessing permissions summary for role {role_id}")
        
        response_data = await perm_service.get_role_permissions_summary(role_id)
        if not response_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
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
        logger.info(f"User {current_user['id']} validating access for user {user_id}")
        
        response_data = await perm_service.validate_user_access(user_id, resource, action)
        
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


# =============================================================================
# SETUP ENDPOINTS (NO AUTHENTICATION)
# =============================================================================

@router.post("/setup/bulk-create", 
             response_model=BulkPermissionResponseDTO,
             summary="Setup: Bulk create permissions",
             description="Create multiple permissions at once (NO AUTH - SETUP ONLY)")
async def setup_bulk_create_permissions(bulk_data: BulkPermissionCreateDTO):
    """Bulk create permissions for system setup (NO AUTH)"""
    try:
        permissions_data = [perm.dict() for perm in bulk_data.permissions]
        result = await perm_repo.bulk_create(permissions_data)
        
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
async def setup_create_permission(permission_data: PermissionCreateDTO):
    """Create a single permission for system setup (NO AUTH)"""
    try:
        # Check if permission with same name already exists
        existing_permission = await perm_repo.get_by_name(permission_data.name)
        if existing_permission:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission with name '{permission_data.name}' already exists"
            )
        
        # Create permission
        perm_dict = permission_data.dict()
        perm_id = await perm_repo.create(perm_dict)
        
        # Get created permission
        created_permission = await perm_repo.get_by_id(perm_id)
        perm_response = PermissionResponseDTO(**created_permission, roles_count=0)
        
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
