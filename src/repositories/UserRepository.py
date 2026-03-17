from src.base.BaseRepository import BaseRepository
from typing import Dict, Any
from datetime import datetime
import random

class UserRepository(BaseRepository):
    """User repository for both system and application users"""
    
    def __init__(self, collection_name: str):
        """
        Initialize user repository
        Args:
            collection_name: Either 'system_users' or 'application_users'
        """
        super().__init__(collection_name)
    
    def generate_system_user_id(self) -> str:
        """
        Generate a unique 4-digit ID for system users
        Returns a string like '1000', '1001', etc.
        """
        max_attempts = 100
        for _ in range(max_attempts):
            # Generate random 4-digit number (1000-9999)
            user_id = str(random.randint(1000, 9999))
            
            # Check if ID already exists
            if not self.collection.document(user_id).get().exists:
                return user_id
        
        # If we couldn't find a unique ID after max_attempts, raise error
        raise Exception("Unable to generate unique 4-digit user ID. All IDs may be taken.")
    
    def create_system_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new system user with a 4-digit ID
        """
        # Generate 4-digit ID
        user_id = self.generate_system_user_id()
        
        # Create document with custom ID
        doc_ref = self.collection.document(user_id)
        data['id'] = user_id
        data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()
        if 'is_active' not in data:
            data['is_active'] = True
        if 'is_deleted' not in data:
            data['is_deleted'] = False
        
        doc_ref.set(data)
        return data