from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

_VALID_CATEGORIES = {"system", "application"}
_VALID_ACTIONS = {"create", "read", "update", "delete", "list", "manage", "status"}


class PermissionBase(BaseModel):
    """Base permission schema"""
    category: str = Field(..., description="Permission category: system or application")
    resource: str = Field(..., min_length=1, max_length=100)
    action: str = Field(..., min_length=1, max_length=50)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in _VALID_CATEGORIES:
            raise ValueError(f'category must be one of: {", ".join(sorted(_VALID_CATEGORIES))}')
        return v

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in _VALID_ACTIONS:
            raise ValueError(f'action must be one of: {", ".join(sorted(_VALID_ACTIONS))}')
        return v


class PermissionCreate(PermissionBase):
    """Create permission schema"""
    pass


class PermissionUpdate(BaseModel):
    """Update permission schema"""
    category: Optional[str] = None
    resource: Optional[str] = Field(None, min_length=1, max_length=100)
    action: Optional[str] = Field(None, min_length=1, max_length=50)
    is_active: Optional[bool] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_CATEGORIES:
            raise ValueError(f'category must be one of: {", ".join(sorted(_VALID_CATEGORIES))}')
        return v

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_ACTIONS:
            raise ValueError(f'action must be one of: {", ".join(sorted(_VALID_ACTIONS))}')
        return v


class PermissionResponse(BaseModel):
    """Permission response schema"""
    id: int
    category: str
    resource: str
    action: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PermissionBulkCreate(BaseModel):
    """Bulk create permissions schema"""
    permissions: List[PermissionCreate] = Field(..., min_length=1)
