from src.base.BaseModel import BaseModel
from typing import Optional

class Permission(BaseModel):
    """Permission model"""
    
    def __init__(self):
        super().__init__()
        self.name: str = ""  # e.g., "system:users:create"
        self.description: str = ""
        self.category: str = ""  # e.g., "system" or "application"
        self.resource: str = ""  # e.g., "users", "roles", "orders"
        self.action: str = ""  # e.g., "create", "read", "update", "delete", "*"
        self.is_system: bool = False  # True for built-in permissions that cannot be deleted