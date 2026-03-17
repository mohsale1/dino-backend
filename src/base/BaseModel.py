from datetime import datetime, timezone
from typing import Optional

class BaseModel:
    """Base model with common fields for all models"""
    
    def __init__(self):
        self.id: Optional[str] = None
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)
        self.is_active: bool = True
        self.is_deleted: bool = False
        self.deleted_at: Optional[datetime] = None
        self.restored_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            else:
                data[key] = value
        return data
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create model instance from dictionary"""
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now(timezone.utc)
    
    def soft_delete(self):
        """Mark as soft deleted"""
        self.is_deleted = True
        self.is_active = False
        self.deleted_at = datetime.now(timezone.utc)
        self.update_timestamp()
    
    def restore(self):
        """Restore from soft delete"""
        self.is_deleted = False
        self.is_active = True
        self.restored_at = datetime.now(timezone.utc)
        self.update_timestamp()
