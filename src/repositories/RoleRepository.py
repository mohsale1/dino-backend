from src.base.BaseRepository import BaseRepository
from typing import List, Dict, Any, Optional
from google.cloud.firestore_v1 import FieldFilter


class RoleRepository(BaseRepository):
    """Role repository"""

    def __init__(self):
        super().__init__("roles")

    def get_by_type(self, role_type: int) -> List[Dict[str, Any]]:
        """Get all roles by type (0=System, 1=Application)"""
        return self.get_all(filters={"role_type": role_type})

    def get_by_name_and_type(self, name: str, role_type: int) -> Optional[Dict[str, Any]]:
        """Get role by name and type"""
        docs = self.collection.where(filter=FieldFilter("name", "==", name)).where(filter=FieldFilter("role_type", "==", role_type)).limit(1).get()
        if docs:
            return docs[0].to_dict()
        return None
