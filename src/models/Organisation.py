from src.base.BaseModel import BaseModel
from typing import Optional, Dict, Any

class Organization(BaseModel):
    """Organization model - venue/branch under a workspace"""
    
    def __init__(self):
        super().__init__()
        self.name: str = ""  # e.g., "McDonald's Downtown"
        self.description: Optional[str] = None
        self.workspace_id: str = ""  # Workspace this organization belongs to
        self.organization_type: int = 0  # 0 = FOOD, 1 = NON_FOOD
        self.order_type: int = 0  # 0 = Online (self-service), 1 = Manual (Counter-based)