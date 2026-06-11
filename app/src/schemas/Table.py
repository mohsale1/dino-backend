from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TableStatus = Literal['available', 'occupied', 'reserved', 'out_of_service']


class TableBase(BaseModel):
    table_number: str = Field(..., min_length=1, max_length=50)
    area_id: int
    capacity: int = Field(default=4, ge=1)
    status: TableStatus = 'available'


class TableCreate(TableBase):
    persona_id: int


class TableUpdate(BaseModel):
    table_number: Optional[str] = Field(None, min_length=1, max_length=50)
    capacity: Optional[int] = Field(None, ge=1)
    status: Optional[TableStatus] = None


class TableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    table_number: str
    area_id: int
    persona_id: int
    capacity: int
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
