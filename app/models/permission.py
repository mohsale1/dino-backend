"""
Permission Models
Database entities and DTOs for permission management
"""
from pydantic import Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.base import BaseSchema, BaseDTO, TimestampMixin


# =============================================================================
# DATABASE ENTITY
# =============================================================================

class Permission(BaseSchema, TimestampMixin):
    """Permission collection schema"""
    id: str
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)
    scope: str = Field(..., min_length=1, max_length=50)
    
    @field_validator('name')
    @classmethod
    def validate_name_format(cls, v):
        """Validate permission name format - must use dot separator"""
        if '.' not in v:
            raise ValueError('Name must follow resource.action format (e.g., venue.read)')
        
        parts = v.split('.')
        if len(parts) < 2:
            raise ValueError('Name must follow resource.action format (e.g., venue.read)')
        
        return v


# =============================================================================
# DTOs
# =============================================================================

class PermissionCreateDTO(BaseDTO):
    """DTO for creating permissions"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)
    scope: str = Field(..., min_length=1, max_length=50)
    
    @field_validator('name')
    @classmethod
    def validate_name_format(cls, v):
        """Validate permission name format - must use dot separator"""
        if '.' not in v:
            raise ValueError('Name must follow resource.action format (e.g., venue.read)')
        
        parts = v.split('.')
        if len(parts) < 2:
            raise ValueError('Name must follow resource.action format (e.g., venue.read)')
        
        return v


class PermissionUpdateDTO(BaseDTO):
    """DTO for updating permissions"""
    description: Optional[str] = Field(None, max_length=500)


class PermissionResponseDTO(BaseDTO):
    """Complete permission response DTO"""
    id: str
    name: str
    description: str
    resource: str
    action: str
    scope: str
    roles_count: int = Field(default=0, description="Number of roles with this permission")
    created_at: datetime


class PermissionFiltersDTO(BaseDTO):
    """Permission filtering options DTO"""
    name: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    scope: Optional[str] = None
    search: Optional[str] = None


class PermissionCategoryDTO(BaseDTO):
    """Permission category DTO"""
    name: str
    display_name: str
    description: str
    permissions: List[PermissionResponseDTO] = Field(default_factory=list)


class PermissionMatrixDTO(BaseDTO):
    """Permission matrix DTO"""
    resources: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    matrix: Dict[str, Dict[str, Optional[PermissionResponseDTO]]] = Field(default_factory=dict)


class PermissionStatisticsDTO(BaseDTO):
    """Permission statistics DTO"""
    total_permissions: int = 0
    permissions_by_resource: Dict[str, int] = Field(default_factory=dict)
    permissions_by_action: Dict[str, int] = Field(default_factory=dict)
    permissions_by_category: Dict[str, int] = Field(default_factory=dict)
    unused_permissions: int = 0


class BulkPermissionCreateDTO(BaseDTO):
    """DTO for bulk permission creation"""
    permissions: List[PermissionCreateDTO] = Field(..., min_items=1, max_items=100)


class BulkPermissionResponseDTO(BaseDTO):
    """Response DTO for bulk operations"""
    success: bool = True
    created: int = 0
    skipped: int = 0
    errors: List[str] = Field(default_factory=list)
    created_permissions: List[PermissionResponseDTO] = Field(default_factory=list)


class PermissionCheckDTO(BaseDTO):
    """Permission check result DTO"""
    has_permission: bool
    reason: Optional[str] = None


class SetupPermissionDTO(BaseDTO):
    """DTO for permission setup during system initialization"""
    name: str
    description: str
    resource: str
    action: str
    scope: str