from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AreaBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    workspace_id: int
    is_available: bool = True


class AreaCreate(AreaBase):
    persona_id: Optional[int] = None


class AreaUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_available: Optional[bool] = None
    persona_id: Optional[int] = None
    is_active: Optional[bool] = None


class AreaResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    workspace_id: int
    persona_id: Optional[int] = None
    is_available: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
