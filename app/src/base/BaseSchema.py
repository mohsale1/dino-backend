from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any, List, Generic, TypeVar

T = TypeVar('T')

class BaseSchema(BaseModel):
    """Base Pydantic schema with common fields"""

    # from_attributes enables ORM mode; datetime serialization works by default in Pydantic v2
    model_config = ConfigDict(from_attributes=True)

class BaseResponse(BaseSchema):
    """Base response schema"""
    success: bool = True
    message: str = "Operation successful"
    data: Optional[Any] = None

class ErrorResponse(BaseSchema):
    """Error response schema"""
    success: bool = False
    message: str
    error: Optional[str] = None

class PaginationParams(BaseSchema):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")
    order_by: Optional[str] = Field(None, description="Field to order by")
    order_direction: str = Field("asc", description="Order direction (asc/desc)")

class PaginationMeta(BaseSchema):
    """Pagination metadata"""
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool

class PaginatedResponse(BaseResponse):
    """Paginated response schema"""
    data: List[Any]
    pagination: PaginationMeta
