from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class PermissionBase(BaseModel):
    """Base permission schema"""
    name: str = Field(..., min_length=1, max_length=200, description="Permission name (e.g., system:users:create)")
    description: str = Field(..., min_length=1, max_length=500, description="Permission description")
    category: str = Field(..., description="Permission category (system/application)")
    resource: str = Field(..., min_length=1, max_length=100, description="Resource name (e.g., users, roles)")
    action: str = Field(..., min_length=1, max_length=50, description="Action (create, read, update, delete, *)")
    is_system: bool = Field(default=False, description="System permission (cannot be deleted)")
    
    @validator('category')
    def validate_category(cls, v):
        if v not in ['system', 'application']:
            raise ValueError('Category must be either "system" or "application"')
        return v
    
    @validator('action')
    def validate_action(cls, v):
        valid_actions = ['create', 'read', 'update', 'delete', 'list', 'manage', 'moderate', 'status', 'payment', 'subscription']
        if v not in valid_actions:
            raise ValueError(f'Action must be one of: {", ".join(valid_actions)}')
        return v

class PermissionCreate(PermissionBase):
    """Create permission schema"""
    pass

class PermissionUpdate(BaseModel):
    """Update permission schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    category: Optional[str] = None
    resource: Optional[str] = Field(None, min_length=1, max_length=100)
    action: Optional[str] = Field(None, min_length=1, max_length=50)
    is_active: Optional[bool] = None
    
    @validator('category')
    def validate_category(cls, v):
        if v is not None and v not in ['system', 'application']:
            raise ValueError('Category must be either "system" or "application"')
        return v
    
    @validator('action')
    def validate_action(cls, v):
        if v is not None:
            valid_actions = ['create', 'read', 'update', 'delete', 'list', 'manage', 'moderate', 'status', 'payment', 'subscription']
            if v not in valid_actions:
                raise ValueError(f'Action must be one of: {", ".join(valid_actions)}')
        return v

class PermissionResponse(PermissionBase):
    """Permission response schema"""
    id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    is_deleted: bool
    
    class Config:
        from_attributes = True

class PermissionBulkCreate(BaseModel):
    """Bulk create permissions schema"""
    permissions: list[PermissionCreate] = Field(..., min_items=1, description="List of permissions to create")