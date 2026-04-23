from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_serializer

T = TypeVar('T')


class BaseSchema(BaseModel):
    """Base Pydantic schema with common fields."""

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def _serialize_datetime(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        return value


class BaseResponse(BaseModel):
    """Base response schema."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    message: str = "Operation successful"
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Error response schema."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = False
    message: str
    error: Optional[str] = None


class PaginationParams(BaseModel):
    """Pagination parameters."""

    model_config = ConfigDict(from_attributes=True)

    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")
    order_by: Optional[str] = Field(None, description="Field to order by")
    order_direction: str = Field("asc", description="Order direction (asc/desc)")


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    model_config = ConfigDict(from_attributes=True)

    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseResponse):
    """Paginated response schema."""

    data: List[Any]
    pagination: PaginationMeta
