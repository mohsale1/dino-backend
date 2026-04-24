from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    mobile: str = Field(..., min_length=7, max_length=30, pattern=r'^\+?[0-9\s\-\(\)]{7,30}$')


class CustomerCreate(CustomerBase):
    persona_id: Optional[int] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    mobile: Optional[str] = Field(None, min_length=7, max_length=30, pattern=r'^\+?[0-9\s\-\(\)]{7,30}$')
    persona_id: Optional[int] = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    mobile: str
    workspace_id: int
    persona_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
