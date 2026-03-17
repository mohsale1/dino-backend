from src.base.BaseModel import BaseModel
from typing import List

class Role(BaseModel):
    """Role model"""
    
    def __init__(self):
        super().__init__()
        self.name: str = ""
        self.role_type: int = 0  # 0 = System, 1 = Application
        self.description: str = ""
        self.permissions: List[str] = []
        self.is_system: bool = False  # True for built-in roles that cannot be deleted