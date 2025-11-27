"""
Workspace Models
Database entities and DTOs for workspace management
"""
from pydantic import Field
from typing import Optional, List
from datetime import datetime

from app.models.base import BaseSchema, BaseDTO, TimestampMixin


# =============================================================================
# DATABASE ENTITY
# =============================================================================

class Workspace(BaseSchema, TimestampMixin):
    """Workspace collection schema"""
    id: str
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(default=True)


# =============================================================================
# DTOs
# =============================================================================

class WorkspaceCreateDTO(BaseDTO):
    """DTO for creating workspace"""
    name: str = Field(..., min_length=5, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class WorkspaceUpdateDTO(BaseDTO):
    """DTO for updating workspace"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class WorkspaceResponseDTO(BaseDTO):
    """Complete workspace response DTO"""
    id: str
    name: str
    description: Optional[str] = None
    venue_ids: List[str] = Field(default_factory=list)
    is_active: bool
    created_at: datetime
    updated_at: datetime
