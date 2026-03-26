from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class WorkspaceBase(BaseModel):
    """Base workspace schema"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None

class WorkspaceCreate(WorkspaceBase):
    """Create workspace schema"""
    owner_id: str = Field(..., description="User ID of the workspace owner")
    organization_ids: Optional[List[str]] = Field(default_factory=list, description="List of organization IDs")
    referred_by: Optional[str] = Field(None, description="4-digit system user ID who referred this workspace")

class WorkspaceUpdate(BaseModel):
    """Update workspace schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    owner_id: Optional[str] = None
    organization_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None

class WorkspaceResponse(WorkspaceBase):
    """Workspace response schema"""
    id: str
    owner_id: str
    organization_ids: List[str]
    referred_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True