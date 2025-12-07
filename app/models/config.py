"""
Config Models
Database entities and DTOs for system configuration management
"""
from pydantic import Field
from typing import Optional, Any
from datetime import datetime

from app.models.base import BaseSchema, BaseDTO, TimestampMixin


# =============================================================================
# DATABASE ENTITY
# =============================================================================

class Config(BaseSchema, TimestampMixin):
    """Config collection schema - stores key-value configuration"""
    id: str = Field(..., description="Configuration key (e.g., dino.registration.code) - used as document ID")
    value: Any = Field(..., description="Configuration value (can be string, number, boolean, etc.)")


# =============================================================================
# DTOs
# =============================================================================

class ConfigCreateDTO(BaseDTO):
    """DTO for creating config"""
    key: str = Field(..., min_length=1, max_length=200, description="Configuration key")
    value: Any = Field(..., description="Configuration value")


class ConfigUpdateDTO(BaseDTO):
    """DTO for updating config"""
    value: Any = Field(..., description="Configuration value")


class ConfigResponseDTO(BaseDTO):
    """Complete config response DTO"""
    id: str
    value: Any
    created_at: datetime
    updated_at: datetime