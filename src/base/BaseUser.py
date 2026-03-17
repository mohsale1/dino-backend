from src.base.BaseModel import BaseModel
from typing import Optional

class BaseUser(BaseModel):
    """Base user model with common user fields"""
    
    def __init__(self):
        super().__init__()
        self.email: str = ""
        self.password_hash: str = ""
        self.first_name: str = ""
        self.last_name: str = ""
        self.phone: Optional[str] = None
        self.role_id: str = ""
    
    @property
    def full_name(self) -> str:
        """Get full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def to_dict(self, include_password: bool = False) -> dict:
        """Convert user to dictionary"""
        data = super().to_dict()
        if not include_password:
            data.pop('password_hash', None)
        return data
