"""
Pydantic v2 schemas for the Review resource.
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from src.base.BaseSchema import BaseSchema


class ReviewCreate(BaseSchema):
    """Payload for creating a new review."""

    # workspace_id and user_id are always injected server-side from current_user in the route
    rating: float = Field(default=5.0, ge=0.5, le=5.0, multiple_of=0.5, description="Star rating from 0.5 to 5.0 in 0.5 increments")
    comment: Optional[str] = Field(default=None, max_length=2000)


class ReviewUpdate(BaseSchema):
    """Payload for updating an existing review (all fields optional)."""

    # is_active is managed exclusively via delete/restore endpoints
    rating: Optional[float] = Field(default=None, ge=0.5, le=5.0, multiple_of=0.5, description="Star rating from 0.5 to 5.0 in 0.5 increments")
    comment: Optional[str] = Field(default=None, max_length=2000)
    is_approved: Optional[bool] = None


class ReviewResponse(BaseSchema):
    """Full review representation returned to callers."""

    id: int
    workspace_id: int
    user_id: Optional[int] = None
    rating: float
    comment: Optional[str] = None
    is_approved: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Populated by the service layer — not stored in the reviews table
    user_name: Optional[str] = None
