from src.base.BaseModel import BaseModel
from typing import Optional

class Category(BaseModel):
    """Category model - represents item categories"""
    
    def __init__(self):
        super().__init__()
        self.name: str = ""
        self.description: Optional[str] = None
        self.workspace_id: str = ""  # Belongs to a workspace
        self.is_available: bool = True