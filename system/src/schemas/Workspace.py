from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class WorkspaceBase(BaseModel):
    """Base workspace schema"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class WorkspaceCreate(WorkspaceBase):
    """Create workspace schema"""
    owner_id: str = Field(..., description="System user ID (4-digit) of the workspace owner")
    persona_ids: Optional[List[int]] = Field(default_factory=list, description="List of persona IDs")
    referred_by: Optional[str] = Field(None, description="4-digit system user ID who referred this workspace")


class WorkspaceUpdate(BaseModel):
    """Update workspace schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    owner_id: Optional[str] = None
    persona_ids: Optional[List[int]] = None
    is_active: Optional[bool] = None


class WorkspaceResponse(WorkspaceBase):
    """Workspace response schema"""
    id: int
    owner_id: Optional[str] = None
    persona_ids: List[int] = []
    referred_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True
