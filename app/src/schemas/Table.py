from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TableBase(BaseModel):
    table_number: str = Field(..., min_length=1, max_length=50)
    area_id: int
    workspace_id: int
    capacity: int = Field(default=4, ge=1)
    status: str = Field(default="available", max_length=30)


class TableCreate(TableBase):
    display_order: int = 0


class TableUpdate(BaseModel):
    table_number: Optional[str] = Field(None, min_length=1, max_length=50)
    capacity: Optional[int] = Field(None, ge=1)
    status: Optional[str] = Field(None, max_length=30)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class TableResponse(BaseModel):
    id: int
    table_number: str
    area_id: int
    workspace_id: int
    capacity: int
    status: str
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
