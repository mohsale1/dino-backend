from src.base.BaseModel import BaseModel
from typing import Optional

class Item(BaseModel):
    """Item model - represents menu items"""
    
    def __init__(self):
        super().__init__()
        self.name: str = ""
        self.description: Optional[str] = None
        self.category_id: str = ""
        self.workspace_id: str = ""  # Belongs to a workspace
        self.price: float = 0.0
        self.is_available: bool = True
        self.is_vegetarian: Optional[bool] = None  # True = Veg, False = Non-Veg, None = Not Applicable (Retail)
