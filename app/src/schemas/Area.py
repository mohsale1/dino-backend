from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AreaBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    is_available: bool = True


class AreaCreate(AreaBase):
    persona_id: int


class AreaUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    is_available: Optional[bool] = None


class AreaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    persona_id: int
    is_available: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
