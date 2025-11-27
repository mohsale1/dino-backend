"""
Role Models
Database entities and DTOs for role management
"""
from pydantic import Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.base import BaseSchema, BaseDTO, TimestampMixin
from app.models.enums import UserRole


# =============================================================================
# DATABASE ENTITY
# =============================================================================

class Role(BaseSchema, TimestampMixin):
    """Role collection schema"""
    id: str
    name: str = Field(..., description="Role name (e.g., 'superadmin', 'admin', 'operator')")
    description: str = Field(..., max_length=500)
    permission_ids: List[str] = Field(default_factory=list)


# =============================================================================
# DTOs
# =============================================================================

class RoleCreateDTO(BaseDTO):
    """DTO for creating roles"""
    name: str = Field(..., description="Role name (e.g., 'superadmin', 'admin', 'operator')")
    description: str = Field(..., min_length=5, max_length=500, description="Role description")
    permission_ids: List[str] = Field(default_factory=list, description="List of permission IDs")
    
    @validator('name')
    def validate_name(cls, v):
        # Validate role name format
        if not v or len(v.strip()) == 0:
            raise ValueError('Role name cannot be empty')
        # Convert to lowercase for consistency
        return v.lower().strip()


class RoleUpdateDTO(BaseDTO):
    """DTO for updating roles"""
    description: Optional[str] = Field(None, min_length=5, max_length=500)
    permission_ids: Optional[List[str]] = None


class RoleResponseDTO(BaseDTO):
    """Complete role response DTO"""
    id: str
    name: str = Field(..., description="Role name")
    description: str
    permission_ids: List[str] = Field(default_factory=list)
    permissions: List[Dict[str, Any]] = Field(default_factory=list)
    user_count: int = Field(default=0, description="Number of users with this role")
    created_at: datetime
    updated_at: datetime


class RoleFiltersDTO(BaseDTO):
    """Role filtering options DTO"""
    search: Optional[str] = None


class RolePermissionMappingDTO(BaseDTO):
    """Role-permission mapping DTO"""
    role_id: str
    permission_ids: List[str]


class RoleAssignmentDTO(BaseDTO):
    """Role assignment to user DTO"""
    user_id: str
    role_id: str
    workspace_id: Optional[str] = None
    venue_id: Optional[str] = None


class RoleStatisticsDTO(BaseDTO):
    """Role statistics DTO"""
    total_roles: int = 0
    users_by_role: Dict[str, int] = Field(default_factory=dict)


class BulkPermissionAssignmentDTO(BaseDTO):
    """DTO for bulk permission assignment"""
    permission_ids: List[str] = Field(..., description="List of permission IDs to assign")


class SetupRoleDTO(BaseDTO):
    """DTO for role setup during system initialization"""
    name: UserRole
    description: str
    permission_names: List[str] = Field(default_factory=list, description="Permission names to assign")