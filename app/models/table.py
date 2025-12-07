"""
Table Models
Database entities and DTOs for tables and table areas
"""
from pydantic import Field
from typing import Optional
from datetime import datetime

from app.models.base import BaseSchema, BaseDTO, TimestampMixin
from app.models.enums import TableStatus


# =============================================================================
# DATABASE ENTITIES
# =============================================================================

class TableArea(BaseSchema, TimestampMixin):
    """Table area collection schema"""
    id: str
    venue_id: str
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(default=True)
    active: bool = Field(default=True)  # For API compatibility


class Table(BaseSchema, TimestampMixin):
    """Table collection schema"""
    id: str
    venue_id: str
    table_number: str = Field(..., description="Table number as string")
    capacity: int = Field(..., ge=1, le=20)
    area_id: Optional[str] = Field(None, description="Table area ID")
    table_status: TableStatus = TableStatus.AVAILABLE
    is_active: bool = Field(default=True)


# =============================================================================
# DTOs
# =============================================================================

class TableAreaCreateDTO(BaseDTO):
    """DTO for creating table areas"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    venue_id: str
    active: Optional[bool] = Field(default=True, alias="active")

    class Config:
        populate_by_name = True


class TableAreaUpdateDTO(BaseDTO):
    """DTO for updating table areas"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    active: Optional[bool] = None
    is_active: Optional[bool] = None


class TableAreaResponseDTO(BaseDTO):
    """Complete table area response DTO"""
    id: str
    venue_id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    active: bool
    created_at: datetime
    updated_at: datetime


class TableCreateDTO(BaseDTO):
    """DTO for creating tables"""
    table_number: str = Field(..., description="Table number as string")
    capacity: int = Field(..., ge=1, le=20)
    location: Optional[str] = Field(None, max_length=100)
    area_id: Optional[str] = Field(None, description="Table area ID")
    venue_id: str


class TableUpdateDTO(BaseDTO):
    """DTO for updating tables"""
    capacity: Optional[int] = Field(None, ge=1, le=20)
    location: Optional[str] = Field(None, max_length=100)
    area_id: Optional[str] = None
    table_status: Optional[TableStatus] = None
    is_active: Optional[bool] = None


class TableResponseDTO(BaseDTO):
    """Complete table response DTO"""
    id: str
    venue_id: str
    table_number: str
    capacity: int
    location: Optional[str] = None
    area_id: Optional[str] = None
    table_status: TableStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime