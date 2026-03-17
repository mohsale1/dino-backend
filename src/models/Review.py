from src.base.BaseModel import BaseModel
from typing import Optional

class Review(BaseModel):
    """Review/Testimonial model"""
    
    def __init__(self):
        super().__init__()
        self.customer_name: str = ""
        self.role: Optional[str] = None  # e.g., "Owner", "Manager"
        self.restaurant: Optional[str] = None  # Restaurant/Business name
        self.location: Optional[str] = None  # City, State
        self.rating: int = 5  # 1-5 stars
        self.comment: str = ""
        self.avatar: Optional[str] = None  # URL or initials
        self.is_approved: bool = False  # For moderation
        self.workspace_id: Optional[str] = None  # Optional: link to workspace
        self.organization_id: Optional[str] = None  # Optional: link to organization
        self.order_id: Optional[str] = None  # Optional: link to order