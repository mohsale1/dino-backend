"""
Notification Models
Database entities and DTOs for notification management
"""
from pydantic import Field
from typing import Optional, Dict, Any
from datetime import datetime

from app.models.base import BaseSchema, TimestampMixin
from app.models.enums import NotificationType, Priority


# =============================================================================
# DATABASE ENTITY
# =============================================================================

class Notification(BaseSchema, TimestampMixin):
    """Notification collection schema"""
    id: str
    recipient_id: str
    recipient_type: str
    notification_type: NotificationType
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    data: Optional[Dict[str, Any]] = None
    priority: Priority = Priority.NORMAL
    is_read: bool = Field(default=False)
    read_at: Optional[datetime] = None