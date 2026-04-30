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
    persona_id: int = Field(..., ge=1)
    rating: int = Field(default=5, ge=1, le=5, description="Star rating from 1 to 5")
    comment: Optional[str] = Field(default=None, max_length=2000)


class ReviewUpdate(BaseSchema):
    """Payload for updating an existing review (all fields optional)."""

    # is_active is managed exclusively via delete/restore endpoints
    rating: Optional[int] = Field(default=None, ge=1, le=5, description="Star rating from 1 to 5")
    comment: Optional[str] = Field(default=None, max_length=2000)
    is_approved: Optional[bool] = None


class ReviewResponse(BaseSchema):
    """Full review representation returned to callers."""

    id: int
    workspace_id: int
    persona_id: Optional[int] = None
    user_id: Optional[int] = None
    rating: int
    comment: Optional[str] = None
    is_approved: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Populated by the service layer — not stored in the reviews table
    user_name: Optional[str] = None
