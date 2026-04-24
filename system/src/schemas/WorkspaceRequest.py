from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class WorkspaceRequestCreate(BaseModel):
    """Create workspace request schema"""
    email: EmailStr
    workspace_id: int


class WorkspaceRequestReject(BaseModel):
    """Reject workspace request schema"""
    rejection_reason: Optional[str] = None


class WorkspaceRequestResponse(BaseModel):
    """Workspace request response schema"""
    id: int
    email: str
    user_id: Optional[int] = None
    workspace_id: int
    status: str
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True