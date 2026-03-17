from src.base.BaseModel import BaseModel
from typing import Optional

class Table(BaseModel):
    """Table model - represents tables in an area"""
    
    def __init__(self):
        super().__init__()
        self.table_number: str = ""  # e.g., "T1", "T2", "A-101"
        self.area_id: str = ""  # Belongs to an area
        self.workspace_id: str = ""  # Belongs to a workspace
        self.capacity: int = 4  # Number of seats
        self.status: str = "available"  # available, occupied, reserved, maintenance