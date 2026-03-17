from src.base.BaseModel import BaseModel
from typing import Optional

class Area(BaseModel):
    """Area model - represents different areas/sections in an organization"""
    
    def __init__(self):
        super().__init__()
        self.name: str = ""
        self.description: Optional[str] = None
        self.workspace_id: str = ""  # Belongs to a workspace
        self.is_available: bool = True