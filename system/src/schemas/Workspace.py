from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class WorkspaceBase(BaseModel):
    """Base workspace schema"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class WorkspaceCreate(WorkspaceBase):
    """Create workspace schema"""
    owner_id: Optional[int] = None
    referred_by: Optional[int] = None
    persona_ids: Optional[List[int]] = None


class WorkspaceUpdate(BaseModel):
    """Update workspace schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    owner_id: Optional[int] = None
    referred_by: Optional[int] = None
    is_active: Optional[bool] = None
    persona_ids: Optional[List[int]] = None


class WorkspaceResponse(BaseModel):
    """Workspace response schema"""
    id: int
    name: str
    description: Optional[str] = None
    owner_id: Optional[int] = None
    referred_by: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    persona_ids: Optional[List[int]] = None

    class Config:
        from_attributes = True


class WorkspaceBillingUpdate(BaseModel):
    """Update workspace billing schema"""
    plan: Optional[str] = None
    plan_status: Optional[str] = None
    billing_cycle: Optional[str] = None
    billing_email: Optional[str] = None
    billing_name: Optional[str] = None
    billing_address: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_country: Optional[str] = None
    billing_postal_code: Optional[str] = None
    billing_phone: Optional[str] = None
    next_billing_date: Optional[datetime] = None


class WorkspaceBillingResponse(BaseModel):
    """Workspace billing response schema"""
    id: int
    workspace_id: int
    plan: str
    plan_status: str
    billing_cycle: Optional[str] = None
    billing_email: Optional[str] = None
    billing_name: Optional[str] = None
    billing_address: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_country: Optional[str] = None
    billing_postal_code: Optional[str] = None
    billing_phone: Optional[str] = None
    next_billing_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
