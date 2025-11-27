"""
Review Models
Database entities and DTOs for review management
"""
from pydantic import Field
from typing import Optional
from datetime import datetime

from app.models.base import BaseSchema, TimestampMixin
from app.models.enums import FeedbackType


# =============================================================================
# DATABASE ENTITY
# =============================================================================

class Review(BaseSchema, TimestampMixin):
    """Review collection schema"""
    id: str
    venue_id: str
    order_id: str
    customer_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)
    feedback_type: FeedbackType = FeedbackType.OVERALL
    is_verified: bool = Field(default=False)
    helpful_count: int = Field(default=0)